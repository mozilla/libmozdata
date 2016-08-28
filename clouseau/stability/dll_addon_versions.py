# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from collections import defaultdict
import clouseau.utils as utils
import argparse
import clouseau.socorro as socorro
from clouseau.connection import Query
import clouseau.versions


def get(signature, matching_mode, module, addon, product='Firefox', channel=['all'], versions=[], start_date='', limit=0, check_bt=False, verbose=False, ratio=1.):
    if product.lower() == 'firefox':
        product = 'Firefox'

    if channel == [] or channel[0].lower() == 'all':
        channel = ['release', 'beta', 'aurora', 'nightly']
        if product == 'Firefox':
            channel.append('esr')
    else:
        channel = [c.lower() for c in channel]

    if not versions:
        base_versions = clouseau.versions.get(base=True)
        versions_by_channel = socorro.ProductVersions.get_info_from_major(base_versions, product=product)
        versions = []
        for v1 in versions_by_channel.values():
            for v2 in v1:
                versions.append(v2['version'])

    if not start_date:
        start_date = utils.get_date('today', 7)

    if limit <= 0:
        count = []
        socorro.SuperSearch(params={'product': product,
                                    'version': versions,
                                    'signature': matching_mode + signature,
                                    'release_channel': channel,
                                    'date': '>=' + start_date,
                                    '_facets_size': 1,
                                    '_results_number': 0},
                            handler=lambda json: count.append(json['total'])).wait()
        limit = count[0]

    if limit == 0:
        return {'limit': 0}

    def handler_ss(json, data):
        if json['errors']:
            print('Errors occured: %s' % json['errors'])

        if json['total']:
            for signature in json['facets']['signature']:
                for hit in signature['facets']['uuid']:
                    data.append(hit['term'])

    uuids = []
    socorro.SuperSearch(params={'product': product,
                                'version': versions,
                                'signature': matching_mode + signature,
                                'release_channel': channel,
                                'date': '>=' + start_date,
                                '_aggs.signature': 'uuid',
                                '_facets_size': limit,
                                '_results_number': 0},
                        handler=handler_ss, handlerdata=uuids).wait()

    uuids = utils.get_sample(uuids, ratio)
    limit = len(uuids)

    module = [m.lower() for m in module]
    addon = [a.lower() for a in addon]

    if verbose:
        count = [0]
        print('Total uuids: %d' % len(uuids))

    def handler_pc(json, data):
        if verbose:
            count[0] += 1
            c = count[0]
            if c % 100 == 0:
                print('Treated reports: %d' % c)

        addon_version = ''
        if addon:
            for a in json.get('addons', []):
                addon_id = a[0].lower()
                if len(a) == 2 and addon_id in addon:
                    versions = data['versions']
                    addon_version = a[1]
                    versions[addon_id][addon_version] += 1
                    break

            if not addon_version:
                data['not_in_addon'].append(json['uuid'])

        if module:
            dll_version = ''
            json_dump = json['json_dump']
            for m in json_dump.get('modules', []):
                filename = m['filename'].lower()
                if filename in module:
                    versions = data['versions']
                    dll_version = m['version']
                    versions[filename][dll_version] += 1
                    break

            # if addon_version and dll_version and (addon_version == dll_version):
            #     data['match'].append(json['uuid'])

            if check_bt and 'crashing_thread' in json_dump:
                crashing_thread = json_dump['crashing_thread']
                in_bt = False
                for frame in crashing_thread['frames']:
                    if frame['module'].lower() in module:
                        in_bt = True
                        break
                if not in_bt:
                    data['not_in_bt'].append(json['uuid'])

    info = {'versions': defaultdict(lambda: defaultdict(int)), 'limit': limit, 'not_in_bt': [], 'not_in_addon': [], 'match': []}
    queries = []
    for uuid in uuids:
        queries.append(Query(socorro.ProcessedCrash.URL, params={'crash_id': uuid}, handler=handler_pc, handlerdata=info))

    socorro.ProcessedCrash(queries=queries).wait()

    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update status flags in Bugzilla')
    parser.add_argument('-p', '--product', action='store', default='Firefox', help='the product')
    parser.add_argument('-c', '--channel', action='store', nargs='+', default=['all'], help='the channels')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose mode')
    parser.add_argument('-V', '--versions', action='store', nargs='+', default=[], help='the versions')
    parser.add_argument('-l', '--limit', action='store', default=0, type=int, help='the max number of signatures to get')
    parser.add_argument('-m', '--module', action='store', nargs='+', default=[], help='the module name')
    parser.add_argument('-a', '--addon', action='store', nargs='+', default=[], help='the addon name')
    parser.add_argument('-s', '--start-date', dest='start_date', action='store', default='', help='Start date to use to search signatures')
    parser.add_argument('-S', '--signature', action='store', default='', help='signatures to analyze')
    parser.add_argument('-M', '--matching-mode', action='store', default='=', help='a Socorro operator for the signature (e.g. \'=\' for \'is\' or \'~\' for \'contains\' or \'@\' for a regexp)')
    parser.add_argument('-C', '--check', dest='check', action='store_true', default='', help='Check if module is in the backtrace or if addon is in addons list')
    parser.add_argument('-R', '--ratio', action='store', default=1., type=float, help='Ratio of uuids to treat (in [0;1])')
    args = parser.parse_args()

    if not args.module and not args.addon:
        raise Exception('Module or addon name is mandatory (-m and/or -a)')
    if not args.signature:
        raise Exception('Signature is mandatory (-S)')

    info = get(args.signature, args.matching_mode, args.module, args.addon, args.product, args.channel, args.versions, args.start_date, args.limit, args.check, args.verbose, args.ratio)

    if info['limit'] == 0:
        print('%d crash reports have been analyzed.' % info['limit'])
    else:
        print('%d crash reports have been analyzed and the following versions have been found:' % info['limit'])
        for k, vers in info['versions'].items():
            print(' - ' + k)
            for v, c in vers.items():
                print('   - ' + v + ': ' + str(c))

        print('')

        if args.check:
            if args.addon:
                print('The following crashes don\'t use the addon %s:' % args.addon)
                for uuid in info['not_in_addon']:
                    print(uuid)

            if info['not_in_bt']:
                print('The following crashes don\'t contain %s in their backtrace:' % args.module)
                for uuid in info['not_in_bt']:
                    print(uuid)
            else:
                print('All the analyzed backtraces contain %s' % args.module)
