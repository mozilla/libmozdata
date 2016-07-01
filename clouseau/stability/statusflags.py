# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
from pprint import pprint
from requests.utils import quote
import clouseau.socorro as socorro
import clouseau.utils as utils
from clouseau.bugzilla import Bugzilla
import clouseau.versions


def __get_bugs_info(bugids):
    def history_handler(_history, data):
        bots = ['automation@bmo.tld']
        bugid = str(_history['id'])
        history = _history['history']
        if history:
            last_change_date = utils.get_guttenberg_death()
            has_patch = False
            has_assignee = False
            is_fixed = False
            resolved = False
            incomplete = False
            for changes in history:
                if changes['who'] not in bots:
                    last_change_date = utils.get_date_ymd(changes['when'])
                for change in changes['changes']:
                    field_name = change.get('field_name', None)
                    if field_name == 'status':
                        if change.get('added', None) == 'RESOLVED':
                            resolved = True
                        elif change.get('removed', None) == 'RESOLVED':
                            resolved = False
                    elif field_name == 'resolution':
                        added = change.get('added', None)
                        removed = change.get('removed', None)
                        if added == 'FIXED':
                            is_fixed = True
                        elif added == 'INCOMPLETE':
                            incomplete = True
                        if removed == 'FIXED':
                            is_fixed = False
                        elif removed == 'INCOMPLETE':
                            incomplete = False
                    elif field_name == 'flagtypes.name':
                        if not has_patch and 'attachment_id' in change and 'added' in change:
                            added = change['added']
                            if added.startswith('review'):
                                has_patch = True
                    elif field_name == 'assigned_to':
                        has_assignee = change.get('added', None) != 'nobody@mozilla.org'

            data['bugs'][bugid] = {'resolved': resolved,
                                   'incomplete': incomplete,
                                   'fixed': is_fixed,
                                   'patched': has_patch,
                                   'assigned': has_assignee,
                                   'last_change': last_change_date.replace(tzinfo=None)}
        else:
            data['no_history'].append(bugid)

    data = {'no_history': [], 'bugs': {}}
    Bugzilla(bugids=bugids, historyhandler=history_handler, historydata=data).wait()

    if data['no_history']:
        def bug_handler(bug, data):
            last_change_date = utils.get_date_ymd(bug['last_change_time'])
            data[str(bug['id'])] = {'resolved': False,
                                    'incomplete': False,
                                    'fixed': False,
                                    'patched': False,
                                    'assigned': False,
                                    'last_change': last_change_date.replace(tzinfo=None)}

        Bugzilla(bugids=data['no_history'], include_fields=['id', 'last_change_time'], bughandler=bug_handler, bugdata=data['bugs']).wait()

    return data['bugs']


def get_bug_with_one_signature(bugids):
    def bug_handler(bug, data):
        signatures = bug.get('cf_crash_signature', None)
        if signatures and '\r\n' not in signatures:
            # we should have only one signature
            data.add(bug['id'])

    data = set()
    Bugzilla(bugids=bugids, include_fields=['id', 'cf_crash_signature'], bughandler=bug_handler, bugdata=data).wait()

    return data


def get_last_bug(bugids, bugsinfo, min_date=None):
    if not bugids:
        return None

    start_date = utils.get_guttenberg_death().replace(tzinfo=None)
    lasts = {'resolved-unfixed': ['', start_date],
             'resolved-fixed-unpatched': ['', start_date],
             'resolved-fixed-patched': ['', start_date],
             'unresolved-assigned': ['', start_date],
             'unresolved-unassigned': ['', start_date]}
    _lasts = {(True, False, False): lasts['resolved-unfixed'],
              (True, False, True): lasts['resolved-unfixed'],
              (True, True, False): lasts['resolved-fixed-unpatched'],
              (True, True, True): lasts['resolved-fixed-patched'],
              (False, True): lasts['unresolved-assigned'],
              (False, False): lasts['unresolved-unassigned']}

    for bugid in bugids:
        bugid = str(bugid)
        if bugid in bugsinfo:
            info = bugsinfo[bugid]
            if not info['incomplete']:
                i = _lasts[(True, info['fixed'], info['patched'])] if info['resolved'] else _lasts[(False, info['assigned'])]
                if i[1] < info['last_change']:
                    i[0] = bugid
                    i[1] = info['last_change']

    if lasts['resolved-fixed-patched'][1] >= min_date:  # We've a patch in the last days
        return lasts['resolved-fixed-patched'][0]
    elif lasts['resolved-fixed-unpatched'][1] >= min_date:  # The bug has been fixed without a patch (probably a side effect)
        return lasts['resolved-fixed-unpatched'][0]
    elif lasts['resolved-unfixed'][1] >= min_date:  # The bug has been resolved (not fixed)
        return lasts['resolved-unfixed'][0]
    elif lasts['unresolved-assigned'][0]:  # We take the last touched open and assigned bug
        return lasts['unresolved-assigned'][0]
    elif lasts['unresolved-unassigned'][0]:  # We take the last touched open and unassigned bug
        return lasts['unresolved-unassigned'][0]
    else:  # We've only closed bugs and closed before the beginning of the cycle
        return None


def __analyze(signatures, status_flags):
    result = {}
    for signature, data in signatures.items():
        res = {'bugid': None,
               'private': False,
               'firefox': True,
               'resolved': False,
               'affected': [],
               'bugs': None}
        bug = data['selected_bug']
        if bug and bug != 'private':
            if bug['status'] == 'RESOLVED':
                res['resolved'] = True
            for channel in data['affected_channels']:
                sflag = status_flags[channel]
                if sflag not in bug:
                    # probably a Thunderbird bug
                    res['firefox'] = False
                else:
                    sflag = bug[sflag]
                    if sflag == '---':
                        res['affected'].append(channel)
            if res['affected'] or not res['firefox']:
                res['bugid'] = bug['id']
                res['bugs'] = data['bugs']
                result[signature] = res
        elif bug:
            res['private'] = True
            result[signature] = res

    return result


def get(product='Firefox', limit=1000, verbose=False):
    """Get crashes info

    Args:
        product (Optional[str]): the product
        limit (Optional[int]): the number of crashes to get from tcbs

    Returns:
        dict: contains all the info about how to update flags
    """
    p = product.lower()
    if p == 'firefox':
        product = 'Firefox'
    elif p == 'fennecandroid':
        product = 'FennecAndroid'

    channel = ['release', 'beta', 'aurora', 'nightly']
    if product == 'Firefox':
        channel.append('esr')

    base_versions = clouseau.versions.get(base=True)
    versions_by_channel = socorro.ProductVersions.get_info_from_major(base_versions, product=product)
    channel_by_version = {}
    all_versions = []
    start_date_by_channel = {}
    start_date = utils.get_date_ymd('today')
    for chan, versions in versions_by_channel.iteritems():
        start_date_by_channel[chan] = utils.get_date_ymd('tomorrow')
        for v in versions:
            channel_by_version[v['version']] = chan
            d = utils.get_date_ymd(v['start_date'])
            all_versions.append(v['version'])
            if d < start_date:
                start_date = d
            if d < start_date_by_channel[chan]:
                start_date_by_channel[chan] = d

    if verbose:
        print('Versions: %s' % ', '.join(all_versions))
        print('Start dates: %s' % start_date_by_channel)

    start_date = utils.get_date_str(start_date)
    end_date = utils.get_date('today')

    search_date = socorro.SuperSearch.get_search_date(start_date, end_date)
    update_limit = limit <= 0
    if update_limit:
        count = []
        socorro.SuperSearch(params={'product': product,
                                    'version': all_versions,
                                    'date': search_date,
                                    'release_channel': channel,
                                    '_facets_size': 1,
                                    '_results_number': 0},
                            handler=lambda json: count.append(json['total'])).wait()
        limit = count[0]

    signatures = {}

    def handler_ss(json, data, chan=channel_by_version):
        for bucket in json['facets']['signature']:
            s = set()
            signature = bucket['term']
            data[signature] = {'affected_channels': s, 'selected_bug': None, 'bugs': None}
            for c in bucket['facets']['release_channel']:
                s.add(c['term'])

    socorro.SuperSearch(params={'product': product,
                                'version': all_versions,
                                'release_channel': channel,
                                'date': search_date,
                                '_aggs.signature': 'release_channel',
                                '_facets_size': limit,
                                '_results_number': 0},
                        handler=handler_ss, handlerdata=signatures).wait()

    if verbose:
        print('Collected signatures: %d' % len(signatures))

    # get the bugs for each signatures
    bugs_by_signature = socorro.Bugs.get_bugs(signatures.keys())

    if verbose:
        print('Collected bugs in Socorro: Ok')

    # we remove dup bugs
    # for example if we've {1,2,3,4,5} and if 2 is a dup of 5 then the set will be reduced to {1,3,4,5}
    bugs = set()
    for v in bugs_by_signature.values():
        bugs = bugs.union(v)
    dups = Bugzilla.follow_dup(bugs, only_final=False)
    bugs_count = 0
    bugs.clear()
    for s, bugids in bugs_by_signature.items():
        _bugids = set(bugids)
        toremove = set()
        for bugid in bugids:
            chain = dups[str(bugid)]
            if chain:
                elems = []
                for e in chain:
                    e = int(e)
                    if e in _bugids:
                        elems.append(e)
                if elems:
                    elems[-1] = bugid
                    toremove = toremove.union(elems)
        diff = _bugids - toremove
        bugs_by_signature[s] = list(diff)
        bugs_count += len(diff)
        bugs = bugs.union(diff)

    if verbose:
        print('Remove duplicates: Ok')
        print('Bugs to analyze: %d' % bugs_count)

    # TODO: for now we remove the bugs with several signatures
    #       we should handle the different possible cases in a v2
    #       e.g. foo@1234, foo@5678, ...
    bugs = get_bug_with_one_signature(bugs)

    # we get the "better" bug where to update the info
    bugs_history_info = __get_bugs_info(bugs)
    bugs.clear()
    for s, v in bugs_by_signature.items():
        info = signatures[s]
        d = min([start_date_by_channel[c] for c in info['affected_channels']])
        info['selected_bug'] = get_last_bug(v, bugs_history_info, d)
        info['bugs'] = v
        bugs.add(info['selected_bug'])

    if verbose:
        print('Collected last bugs: %d' % len(bugs))

    # get bug info
    include_fields = ['status', 'id', 'cf_crash_signature']
    status_flags = {}
    for c, v in base_versions.iteritems():
        v = str(v)
        if c != 'esr':
            f1 = 'cf_status_firefox' + v
        else:
            f1 = 'cf_status_firefox_esr' + v
        include_fields.append(f1)
        status_flags[c] = f1

    bug_info = {}

    def bug_handler(bug, data):
        data[str(bug['id'])] = bug

    Bugzilla(list(bugs), include_fields=include_fields, bughandler=bug_handler, bugdata=bug_info).get_data().wait()

    if verbose:
        print('Collected bug info: Ok')

    for info in signatures.values():
        bug = info['selected_bug']
        if bug:
            if bug in bug_info:
                info['selected_bug'] = bug_info[bug]
            else:
                info['selected_bug'] = 'private'

    analyzis = __analyze(signatures, status_flags)

    if verbose:
        print('Analysis: Ok\n')

    return {'status_flags': status_flags, 'signatures': analyzis}


def update_status_flags(info):
    status_flags_by_channel = info['status_flags']
    buckets = {}

    # make some buckets to optimize Bugzilla.put
    for sgn, i in info['signatures'].items():
        if i['firefox']:
            affected = i['affected']
            if affected:
                bugid = i['bugid']
                affected.sort()
                affected = tuple(affected)
                if affected in buckets:
                    buckets[affected].append(bugid)
                else:
                    buckets[affected] = [bugid]

    for affected, bugids in buckets.items():
        data = {status_flags_by_channel[a]: 'affected' for a in affected}
        pprint((data, bugids))
        # Bugzilla(bugids).put(data)


def to_html(filename, info):
    with open(filename, 'w') as Out:
        Out.write('<html>\n<body>\n')
        n = 1
        for sgn, i in info['signatures'].items():
            if i['firefox']:
                soc_url = 'https://crash-stats.mozilla.com/signature/?signature=' + quote(sgn)
                bugid = i['bugid']
                bz_url = ' https://bugzil.la/' + str(bugid)
                Out.write('<b>%s.</b> <a href=\'%s\'>%s</a>' % (n, soc_url, sgn))
                n += 1
                if i['resolved']:
                    link_bug = ' <del><a style=\'color:red\' href=\'%s\'>%s</a></del> ' % (bz_url, str(bugid))
                else:
                    link_bug = ' <a href=\'%s\'>%s</a> ' % (bz_url, str(bugid))
                Out.write(link_bug)
                if i['bugs'] and len(i['bugs']) > 1:
                    Out.write('&nbsp;(')
                    bugs = i['bugs']
                    for k in range(len(bugs)):
                        if bugs[k] != bugid:
                            Out.write('<a href=\'https://bugzil.la/%s\'>%s</a>' % (bugs[k], bugs[k]))
                            if k != len(bugs) - 1:
                                Out.write('&nbsp;')
                    Out.write(')&nbsp;')
                Out.write(', '.join(i['affected']) + '<br>\n')
        Out.write('</body>\n</html>\n')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update status flags in Bugzilla')
    parser.add_argument('-p', '--product', action='store', default='Firefox', help='the product')
    parser.add_argument('-l', '--limit', action='store', default=1000, type=int, help='the max number of signatures to get')
    parser.add_argument('-o', '--output', action='store', help='output file (html)')
    parser.add_argument('-u', '--update', action='store_true', help='update Bugzilla')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose mode')
    args = parser.parse_args()

    info = get(product=args.product, limit=args.limit, verbose=args.verbose)

    if args.output:
        to_html(args.output, info)
    if args.update:
        update_status_flags(info)
