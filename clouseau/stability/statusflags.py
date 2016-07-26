# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import re
import functools
import pytz
import logging
from tabulate import (tabulate, TableFormat, DataRow)
from dateutil.relativedelta import relativedelta
from pprint import pprint
from requests.utils import quote
import clouseau.socorro as socorro
import clouseau.utils as utils
from clouseau.bugzilla import Bugzilla
import clouseau.versions
from clouseau.connection import (Connection, Query)
import clouseau.gmail


args_pattern = re.compile('\([^\)]*\)')
template_pattern = re.compile('<[^>]*>')
dll_pattern = re.compile('([^@]+)@0x[a-fA-F0-9]+')
extra_pattern = re.compile('[0-9]+|\.|-')
basic_tablefmt = TableFormat(lineabove=None, linebelowheader=None,
                             linebetweenrows=None, linebelow=None,
                             headerrow=DataRow(" ", " ", ""),
                             datarow=DataRow(" ", " ", ""),
                             padding=0, with_header_hide=None)


def __mk_volume_table(table, headers=()):
    return tabulate(table, headers=headers, tablefmt=basic_tablefmt)


def __get_bugs_info(bugids):
    def history_handler(_history, data):
        bots = ['automation@bmo.tld', 'release-mgmt-account-bot@mozilla.tld']
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
                                   'last_change': last_change_date.astimezone(pytz.utc).replace(tzinfo=None)}
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
                                    'last_change': last_change_date.astimezone(pytz.utc).replace(tzinfo=None)}

        Bugzilla(bugids=data['no_history'], include_fields=['id', 'last_change_time'], bughandler=bug_handler, bugdata=data['bugs']).wait()

    return data['bugs']


def __foo_at_address(signature):
    # Simplify foo.dll@0x1234 to foo.dll
    m = dll_pattern.match(signature)
    if m:
        lib = m.group(1)

        # we remove numbers, dot, dash
        lib = extra_pattern.sub('', lib)
        lib = lib.lower()

        return lib
    else:
        return signature


def __foo_args(signature):
    # Simplify foo<A>(T, U) or foo or foo<B>(V) ... to foo
    signature = args_pattern.sub('', signature)
    signature = template_pattern.sub('', signature)

    return signature


def __name(names, signature):
    return '' if signature in names else signature


def __const(signature):
    return signature.replace('const ', '').replace(' const', '')


def __namespace(signature):
    if '|' not in signature and '::' in signature:
        return signature.split('::')[-1]

    return signature


def __is_same_signatures(signatures, simplifiers):
    # Check of the signatures are the same
    s = set()
    for signature in filter(None, signatures):
        signature = map(lambda s: s.strip(' \t'), signature.split('|'))
        for simplifier in simplifiers:
            signature = map(lambda s: simplifier(s), signature)
        signature = '|'.join(filter(None, signature))
        if signature:
            s.add(signature)

    n = len(s)
    if n in [0, 1]:
        return True
    elif n == 2:
        s = map(lambda sgn: __namespace(sgn), s)
        return s[0] == s[1]
    else:
        return False


def filter_bugs(bugids, product):
    bad = []
    exclude = []
    if product == 'Firefox':
        exclude.append('Firefox for Android')
        exclude.append('Firefox for iOS')

    def bug_handler(bug, data):
        if bug.get('status', 'UNCONFIRMED') == 'UNCONFIRMED' or bug.get('product', '') in exclude:
            return

        signatures = bug.get('cf_crash_signature', None)
        if signatures:
            if '\r\n' not in signatures:
                # we should have only one signature
                data.add(bug['id'])
            else:
                if '[@' in signatures:
                    signatures = map(lambda s: s.strip(' \t\r\n'), signatures.split('[@'))
                    signatures = map(lambda s: s[:-1].strip(' \t\r\n'), filter(None, signatures))

                    if __is_same_signatures(signatures, [functools.partial(__name, ['@0x0',
                                                                                    'F1398665248_____________________________',
                                                                                    'unknown',
                                                                                    'OOM',
                                                                                    'hang',
                                                                                    'small',
                                                                                    '_purecall',
                                                                                    'je_free',
                                                                                    'large']),
                                                         __foo_at_address,
                                                         __foo_args,
                                                         __const]):
                        data.add(bug['id'])
                    else:
                        bad.append(signatures)
        else:
            data.add(bug['id'])

    data = set()
    Bugzilla(bugids=bugids, include_fields=['id', 'cf_crash_signature', 'status', 'product'], bughandler=bug_handler, bugdata=data).wait()

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

    one_year_ago = utils.get_date_ymd('today') - relativedelta(years=1)

    if lasts['resolved-fixed-patched'][1] >= min_date:  # We've a patch in the last days
        return lasts['resolved-fixed-patched'][0]
    elif lasts['resolved-fixed-unpatched'][1] >= min_date:  # The bug has been fixed without a patch (probably a side effect)
        return lasts['resolved-fixed-unpatched'][0]
    elif lasts['resolved-unfixed'][1] >= min_date:  # The bug has been resolved (not fixed)
        return lasts['resolved-unfixed'][0]
    elif lasts['unresolved-assigned'][1] >= one_year_ago:  # We take the last touched open and assigned bug
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
               'platforms': [],
               'bugs': None,
               'trend': {}}
        bug = data['selected_bug']
        if bug and bug != 'private':
            if bug['status'] == 'RESOLVED':
                res['resolved'] = True
            for ac in data['affected_channels']:
                channel = ac[0]
                sflag = status_flags[channel]
                if sflag not in bug:
                    # probably a Thunderbird bug
                    res['firefox'] = False
                else:
                    sflag = bug[sflag]
                    if sflag == '---':
                        res['affected'].append(ac)
            if res['affected'] or not res['firefox']:
                res['bugid'] = bug['id']
                res['bugs'] = data['bugs']
                res['platforms'] = data['platforms']
                result[signature] = res
        elif bug:
            res['private'] = True
            result[signature] = res

    return result


def __get_signatures_from_bug_ids(bugids):
    if not bugids:
        return set()

    def bug_handler(bug, data):
        signatures = bug.get('cf_crash_signature', None)
        if signatures:
            signatures = map(lambda s: s.strip(' \t\r\n'), signatures.split('[@'))
            signatures = map(lambda s: s[:-1].strip(' \t\r\n'), filter(None, signatures))
            for s in filter(None, signatures):
                data.add(s)

    data = set()
    Bugzilla(bugids=bugids, include_fields=['cf_crash_signature'], bughandler=bug_handler, bugdata=data).wait()

    return data


def __get_signatures(limit, product, versions, channel, search_date, signatures, bug_ids, verbose):
    if limit <= 0:
        count = []
        socorro.SuperSearch(params={'product': product,
                                    'version': versions,
                                    'date': search_date,
                                    'release_channel': channel,
                                    '_facets_size': 1,
                                    '_results_number': 0},
                            handler=lambda json: count.append(json['total'])).wait()
        limit = count[0]

    __warn('Maximum signatures to collect: %d' % limit, verbose)

    __signatures = {}

    known_platforms = {'Windows NT', 'Mac OS X', 'Linux'}
    known_wtf_platforms = {'0x00000000', ''}

    def handler_ss(json, data):
        for bucket in json['facets']['signature']:
            l1 = []
            l2 = []
            signature = bucket['term']
            data[signature] = {'affected_channels': l1,
                               'platforms': l2,
                               'selected_bug': None,
                               'bugs': None}
            facets = bucket['facets']
            for c in facets['release_channel']:
                l1.append((c['term'], c['count']))
            for p in facets['platform']:
                os = p['term']
                if os and os in known_platforms:
                    if os == 'Windows NT':
                        os = 'Windows'
                    l2.append(os)
                elif os not in known_wtf_platforms:
                    pprint('Unknown os: %s' % os)

    if signatures or bug_ids:
        s = __get_signatures_from_bug_ids(bug_ids)
        signatures = list(s.union(signatures))
        queries = []
        for sgns in Connection.chunks(signatures, 10):
            queries.append(Query(socorro.SuperSearch.URL,
                                 {'signature': ['=' + s for s in sgns],
                                  'product': product,
                                  'version': versions,
                                  'release_channel': channel,
                                  'date': search_date,
                                  '_aggs.signature': ['release_channel', 'platform'],
                                  '_facets_size': limit,
                                  '_results_number': 0},
                                 handler=handler_ss, handlerdata=__signatures))
        socorro.SuperSearch(queries=queries).wait()
    else:
        socorro.SuperSearch(params={'product': product,
                                    'version': versions,
                                    'release_channel': channel,
                                    'date': search_date,
                                    '_aggs.signature': ['release_channel', 'platform'],
                                    '_facets_size': limit,
                                    '_results_number': 0},
                            handler=handler_ss, handlerdata=__signatures, timeout=300).wait()

    return __signatures


def __warn(str, verbose):
    if verbose:
        print(str)
    logging.debug(str)


def get(product='Firefox', limit=1000, verbose=False, search_start_date='', signatures=[], bug_ids=[]):
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

    __warn('Versions: %s' % ', '.join(all_versions), verbose)
    __warn('Start dates: %s' % start_date_by_channel, verbose)

    end_date = utils.get_date('today')
    if search_start_date:
        search_date = socorro.SuperSearch.get_search_date(search_start_date, end_date)
    else:
        search_date = socorro.SuperSearch.get_search_date(utils.get_date_str(start_date), end_date)

    signatures = __get_signatures(limit, product, all_versions, channel, search_date, signatures, bug_ids, verbose)

    __warn('Collected signatures: %d' % len(signatures), verbose)

    # get the bugs for each signatures
    bugs_by_signature = socorro.Bugs.get_bugs(signatures.keys())

    # if we've some bugs in bug_ids then we must remove the other ones for a given signature
    if bug_ids:
        bids = set(bug_ids)
        for s, bugids in bugs_by_signature.items():
            inter = bids.intersection(bugids)
            if inter:
                bugs_by_signature[s] = inter

    __warn('Collected bugs in Socorro: Ok', verbose)

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

    __warn('Remove duplicates: Ok', verbose)
    __warn('Bugs to analyze: %d' % bugs_count, verbose)

    # we filter the bugs to remove meaningless ones
    if not bug_ids:
        bugs = filter_bugs(bugs, product)

    # we get the "better" bug where to update the info
    bugs_history_info = __get_bugs_info(bugs)

    crashes_to_reopen = []
    bugs.clear()
    tomorrow = utils.get_date_ymd('tomorrow')
    for s, v in bugs_by_signature.items():
        info = signatures[s]
        if v:
            min_date = tomorrow
            for i in info['affected_channels']:
                if i[0] != 'esr':
                    d = start_date_by_channel[i[0]]
                    if d < min_date:
                        min_date = d

            bug_to_touch = get_last_bug(v, bugs_history_info, min_date)
            if not bug_to_touch:
                crashes_to_reopen.append(s)
        else:
            bug_to_touch = None

        info['selected_bug'] = bug_to_touch
        info['bugs'] = v
        if bug_to_touch:
            bugs.add(bug_to_touch)

    __warn('Collected last bugs: %d' % len(bugs), verbose)

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

    __warn('Collected bug info: Ok', verbose)

    for info in signatures.values():
        bug = info['selected_bug']
        if bug:
            if bug in bug_info:
                info['selected_bug'] = bug_info[bug]
            else:
                info['selected_bug'] = 'private'

    analysis = __analyze(signatures, status_flags)

    __warn('Analysis: Ok', verbose)

    # Now get the number of crashes for each signature
    queries = []
    trends = {}
    signatures_by_chan = {}
    default_trend_by_chan = {}
    today = utils.get_date_ymd('today')
    ref_w = today.isocalendar()[1]

    def get_past_week(date):
        isodate = date.isocalendar()
        w = isodate[1]
        if w > ref_w:
            return ref_w - w + 53
        else:
            return ref_w - w

    for chan in channel:
        past_w = get_past_week(start_date_by_channel[chan])
        default_trend_by_chan[chan] = {i: 0 for i in range(past_w + 1)}

    for signature, info in analysis.items():
        if info['firefox']:
            data = {}
            trends[signature] = data
            # for chan, volume in info['affected']:
            for chan in channel:
                if chan in signatures_by_chan:
                    signatures_by_chan[chan].append(signature)
                else:
                    signatures_by_chan[chan] = [signature]
                data[chan] = default_trend_by_chan[chan].copy()

    def handler_ss(chan, json, data):
        for facets in json['facets']['histogram_date']:
            d = utils.get_date_ymd(facets['term'])
            w = get_past_week(d)
            s = facets['facets']['signature']
            for signature in s:
                count = signature['count']
                sgn = signature['term']
                data[sgn][chan][w] += count

    for chan, signatures in signatures_by_chan.items():
        if search_start_date:
            search_date = socorro.SuperSearch.get_search_date(search_start_date, end_date)
        else:
            search_date = socorro.SuperSearch.get_search_date(utils.get_date_str(start_date_by_channel[chan]), end_date)

        for sgns in Connection.chunks(signatures, 10):
            queries.append(Query(socorro.SuperSearch.URL,
                                 {'signature': ['=' + s for s in sgns],
                                  'product': product,
                                  'version': all_versions,
                                  'release_channel': chan,
                                  'date': search_date,
                                  '_histogram.date': 'signature',
                                  '_histogram_interval': 1,
                                  '_results_number': 0},
                           handler=functools.partial(handler_ss, chan), handlerdata=trends))
    socorro.SuperSearch(queries=queries).wait()

    __warn('Collected trends: Ok\n', verbose)

    # replace dictionary containing trends by a list
    for signature, i in trends.items():
        for chan, trend in i.items():
            i[chan] = [trend[week] for week in sorted(trend.keys(), reverse=False)]
        analysis[signature]['trend'] = i

    return {'status_flags': status_flags,
            'base_versions': base_versions,
            'start_dates': start_date_by_channel,
            'signatures': analysis}


def update_status_flags(info, update=False):
    status_flags_by_channel = info['status_flags']
    base_versions = info['base_versions']
    channel_order = {'nightly': 0, 'aurora': 1, 'beta': 2, 'release': 3, 'esr': 4}
    platform_order = {'Windows': 0, 'Mac OS X': 1, 'Linux': 2}
    start_date_by_channel = info['start_dates']

    for c, d in start_date_by_channel.items():
        start_date_by_channel[c] = utils.get_date_str(d)

    bugids = []

    for sgn, i in info['signatures'].items():
        if i['firefox']:
            volumes = {}
            data = {}
            bugid = i['bugid']
            bugids.append(str(bugid))
            for channel, volume in i['affected']:
                data[status_flags_by_channel[channel]] = 'affected'
                volumes[channel] = volume
            if volumes:
                comment = 'Crash volume for signature \'%s\':\n' % sgn
                table = []
                for p in sorted(volumes.items(), key=lambda k: channel_order[k[0]]):
                    affected_chan = p[0]
                    affected_version = base_versions[p[0]]
                    start_date = start_date_by_channel[p[0]]
                    volume = p[1]
                    plural = '' if volume == 1 else 'es'
                    table.append(['- %s' % affected_chan,
                                  '(version %d):' % affected_version,
                                  '%d crash%s from %s.' % (volume, plural, start_date)])
                comment += __mk_volume_table(table)

                table = []
                empty = False
                N = -1
                for chan, trend in sorted(i['trend'].items(), key=lambda k: channel_order[k[0]]):
                    if len(trend) >= 1:
                        # we remove data for this week
                        del(trend[0])
                    if len(trend) >= 8:  # keep only the last seven weeks
                        trend = trend[:7]

                    if not trend:
                        empty = True
                        break

                    N = max(N, len(trend))
                    row = [str(n) for n in trend]
                    row.insert(0, '- %s' % chan)
                    table.append(row)

                if not empty:
                    comment += '\n\nCrash volume on the last weeks:\n'
                    headers = ['']
                    for w in range(1, N + 1):
                        headers.append('Week N-%d' % w)
                    comment += __mk_volume_table(table, headers=headers)

                platforms = i['platforms']
                if platforms:
                    comment += '\n\nAffected platform'
                    if len(platforms) >= 2:
                        comment += 's'
                        platforms = sorted(platforms, key=lambda k: platform_order[k])
                    comment += ': ' + ', '.join(platforms)
                # print(comment)
                data['comment'] = {'body': comment}
            if update:
                Bugzilla([str(bugid)]).put(data)
                pprint((bugid, data))
            else:
                pprint((bugid, data))

    if update:
        links = '\n'.join(Bugzilla.get_links(bugids))
        print(links)


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
    parser.add_argument('-s', '--start-date', dest='start_date', action='store', default='', help='Start date to use to search signatures')
    parser.add_argument('-u', '--update', action='store_true', help='update Bugzilla')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose mode')
    parser.add_argument('-d', '--dry-run', dest='dry_run', action='store_true', help='avoid to push on Bugzilla')
    parser.add_argument('-S', '--signatures', action='store', nargs='+', default=[], help='signatures to analyze')
    parser.add_argument('-B', '--bug-ids', dest='bug_ids', action='store', nargs='+', default=[], help='signatures in bugs to analyze')
    parser.add_argument('-L', '--log', action='store', default='/tmp/statusflags.log', help='file where to put log')
    parser.add_argument('-n', '--nag-dev', dest='nag_dev', action='store', default='', help='send an email to the dev when errors')
    args = parser.parse_args()

    if args.log:
        logging.basicConfig(filename=args.log, filemode='w', level=logging.DEBUG)

    try:
        info = get(product=args.product, limit=args.limit, verbose=args.verbose, search_start_date=args.start_date, signatures=args.signatures, bug_ids=args.bug_ids)

        if args.output:
            to_html(args.output, info)
        if args.update:
            update_status_flags(info, update=not args.dry_run)
    except:
        if args.verbose:
            raise

        logging.exception('An exception occured...')
        if args.nag_dev:
            with open(args.log, 'r') as f:
                data = f.read()
                clouseau.gmail.send(args.nag_dev, 'Error in statusflags.py', data)
