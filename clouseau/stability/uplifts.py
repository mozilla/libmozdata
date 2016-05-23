# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import six
from pprint import pprint
import clouseau.socorro as socorro
import clouseau.utils as utils
from clouseau.connection import Query
from clouseau.bugzilla import Bugzilla


def __tcbs_handler(json, data):
    for crash in json['crashes']:
        data.append(crash)


def __bug_handler(bug, data):
    data[str(bug['id'])] = bug


def __analyze(signatures, status_flags, tracking_flags):
    result = {}
    for signature, data in signatures.iteritems():
        res = {'bugid': None,
               'original_bugid': None,
               'signature_in_bug': True,
               'private': False,
               'affected': [],
               'uplift': [],
               'tracked': [],  # if the flag isn't '-' then we could track it
               'assigned': True,  # is the bug assigned ?
               'firefox': True,  # Firefox bug: sometimes it's a Thunderbird crash & we don't have the good tracking/status flags
               'topcrash': False,  # is the topcrash keyword is in bug 'Keywords' ?
               'info': {}}
        bug = data['bug']
        if bug and bug != 'private':
            if 'cf_crash_signature' not in bug or signature not in bug['cf_crash_signature']:
                res['signature_in_bug'] = False
            for kw in bug.get('keywords', None):
                if 'topcrash' in kw:
                    res['topcrash'] = True
                    break
            status = bug['status']
            resolution = bug['resolution']
            is_fixed = False
            if status == 'NEW':
                res['assigned'] = False
            elif (status == 'RESOLVED' and resolution == 'FIXED') or (status == 'ASSIGNED' and bug[status_flags['nightly']] == 'fixed'):
                is_fixed = True

            for info in data['info']:
                channel = info['channel']
                if channel != 'nightly':
                    sflag = status_flags[channel]
                    if sflag not in bug:
                        # probably a Thunderbird bug
                        res['firefox'] = False
                    else:
                        add_channel = False
                        sflag = bug[sflag]
                        if sflag == '---':
                            res['affected'].append(channel)
                            add_channel = True
                        if is_fixed:
                            if sflag != 'fixed' and sflag != 'wontfix':
                                tflag = bug[tracking_flags[channel]]
                                if tflag == '+' or tflag == 'blocking':
                                    res['uplift'].append(channel)
                                    add_channel = True
                                elif tflag != '-':
                                    res['tracked'].append(channel)
                                    add_channel = True
                        if add_channel:
                            res['info'][channel] = info
            if not res['signature_in_bug'] or res['affected'] or res['info'] or not res['firefox'] or not res['topcrash']:
                res['bugid'] = bug['id']
                res['original_bugid'] = data['original_bug']
                result[signature] = res

        elif bug:
            res['private'] = True
            res['original_bugid'] = data['original_bug']
            result[signature] = res

    return result


def get(date='today', product='Firefox', versions=None, duration=7, tcbs_limit=50, crash_type='all', credentials=None):
    """Get crashes info

    Args:
        date (Optional[str]): the final date
        versions (Optional[List[str]]): the versions to treat
        product (Optional[str]): the product
        duration (Optional[int]): the duration to retrieve the data
        tcbs_limit (Optional[int]): the number of crashes to get from tcbs
        crash_type (Optional[str]): 'all' (default) or 'browser' or 'content' or 'plugin'
        credentials (Optional[dict]): credentials

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

    if not versions:
        _versions = socorro.ProductVersions.get_active(product=product, remove_dates=True, credentials=credentials)
        # get the last version
        versions = {}
        for k, v in _versions.iteritems():
            versions[k] = [v[0]]

    end_date = utils.get_date(date)

    if crash_type and isinstance(crash_type, six.string_types):
        crash_type = [crash_type]

    # get top crashes for each channel and crash_type
    tcbs = {}
    base = {'product': product,
            'crash_type': None,
            'version': None,
            'limit': tcbs_limit,
            'duration': 24 * duration,
            'end_date': end_date}

    queries = []
    for ct in crash_type:
        tcbs[ct] = {}
        for c in channel:
            tcbs[ct][c] = {}
            for v in versions[c]:
                _list = []
                tcbs[ct][c][v] = _list
                cparams = base.copy()
                cparams['version'] = v
                cparams['crash_type'] = ct
                queries.append(Query(socorro.TCBS.URL, cparams, __tcbs_handler, _list))

    socorro.TCBS(queries=queries, credentials=credentials).wait()

    # structure the data by signatures
    signatures = {}
    for ct, v1 in tcbs.iteritems():
        for chan, v2 in v1.iteritems():
            for version, crashes in v2.iteritems():
                for crash in crashes:
                    signature = crash['signature']
                    count = crash['count']
                    rank = crash['currentRank'] + 1
                    is_startup_crash = round(crash['startup_percent'] * 100.) > 50.
                    _info = {'channel': chan,
                             'version': version,
                             'count': count,
                             'rank': rank,
                             'startup_crash': is_startup_crash}
                    if signature in signatures:
                        signatures[signature]['info'].append(_info)
                    else:
                        signatures[signature] = {'bug': None, 'original_bug': None, 'info': [_info]}

    # get the bugs for each signatures
    bugs_by_signature = socorro.Bugs.get_bugs(signatures.keys(), credentials=credentials)
    bugs = set()
    for b in bugs_by_signature.itervalues():
        bugs.update(b)

    # get the bugs in following the duplicate
    dups = Bugzilla.follow_dup(bugs, credentials=credentials)

    # put the bug info for each signature
    bugs.clear()

    for s, bugids in bugs_by_signature.iteritems():
        _set = set()
        original = {}
        for bugid in bugids:
            bugid = str(bugid)
            d = dups[bugid]
            if d and d != 'cycle':
                original[d] = bugid
                _set.add(d)
            else:
                _set.add(bugid)
        if _set:
            # several bugs can be attached to the signature so just take the last bug
            # TODO: is it a good idea ??
            last_bug = max(_set, key=int)
            signatures[s]['bug'] = last_bug
            if last_bug in original:
                signatures[s]['original_bug'] = original[last_bug]
            bugs.add(last_bug)

    # get bug info
    include_fields = ['status', 'resolution', 'id', 'cf_crash_signature', 'keywords']
    status_flags = {}
    tracking_flags = {}
    for c in channel:
        v = versions[c][0].split('.')[0]
        if c != 'esr':
            f1 = 'cf_status_firefox' + v
            f2 = 'cf_tracking_firefox' + v
        else:
            f1 = 'cf_status_firefox_esr' + v
            f2 = 'cf_tracking_firefox_esr' + v
        include_fields.append(f1)
        include_fields.append(f2)
        status_flags[c] = f1
        tracking_flags[c] = f2

    bug_info = {}
    Bugzilla(list(bugs), include_fields=include_fields, credentials=credentials, bughandler=__bug_handler, bugdata=bug_info).get_data().wait()

    for info in signatures.itervalues():
        bug = info['bug']
        if bug:
            if bug in bug_info:
                info['bug'] = bug_info[bug]
            else:
                info['bug'] = 'private'

    analyzis = __analyze(signatures, status_flags, tracking_flags)

    return {'status_flags': status_flags, 'tracking_flags': tracking_flags, 'signatures': analyzis}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Track')
    parser.add_argument('-d', '--date', action='store', default='today', help='the end date')
    parser.add_argument('-p', '--product', action='store', default='Firefox', help='the product')
    parser.add_argument('-c', '--crashtype', action='store', default='all', help='crash type: \'all\', \'browser\', \'content\' or \'plugin\'')
    parser.add_argument('-D', '--duration', action='store', default=7, help='the duration')
    parser.add_argument('-v', '--versions', action='store', nargs='+', default=None, help='the Firefox versions')
    parser.add_argument('-t', '--tcbslimit', action='store', default=50, help='the Firefox versions')
    parser.add_argument('-C', '--credentials', action='store', default='', help='credentials file to use')

    args = parser.parse_args()

    credentials = utils.get_credentials(args.credentials) if args.credentials else None
    info = get(date=args.date, product=args.product, versions=args.versions, duration=int(args.duration), tcbs_limit=int(args.tcbslimit), crash_type=args.crashtype, credentials=credentials)
    pprint(info)
