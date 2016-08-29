# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import utils
from connection import Query
import socorro


def get_files(uuid, common=None, remove_dup=True):
    """Get the files which appears in a backtrace

    Args:
        uuid (str): crash uuid
        common (list[str]): common part of the different backtraces
        remove_dup (bool): if True, remove the duplicate files

    Returns:
        List[str]: a list of the files which appears in the backtrace
    """

    def handler(json, data):
        frames = json['json_dump']['threads'][json['crashedThread']]['frames']
        n = len(common) if common else -1
        if remove_dup:
            _files = set()
        for frame in frames:
            if 'file' in frame:
                f = frame['file']
                if not remove_dup or f not in _files:
                    data.append(f)
                    if remove_dup:
                        _files.add(f)
            if n != -1 and 'function' in frame:
                if n <= 1:
                    break
                else:
                    n -= 1

    files = []
    socorro.ProcessedCrash(params={'crash_id': uuid}, handler=handler, handlerdata=files).wait()
    return files


def get_infos(uuids, fraction=0.3):
    """Get info from different backtraces

    Args:
        uuids (List[str]): crash uuids
        fraction (float): the fraction of all the uuids to look in

    Returns:
        dict: info about the different backtraces
    """

    def handler(json, data):
        jd = json['json_dump']
        if 'threads' in jd and 'crashedThread' in json:
            thread_nb = json['crashedThread']
            if thread_nb is not None:
                frames = jd['threads'][thread_nb]['frames']
                data['cpu_name'] = json['cpu_name']
                data['os'] = json['os_pretty_version']
                functions = []
                for frame in frames:
                    if 'function' in frame:
                        functions.append(frame['function'])
                bt = tuple(functions)
                data['cycles'] = __cycles_detection(functions)
                data['functions'] = bt
        if 'crash_info' in jd:
            data['address'] = jd['crash_info']['address']

    base = {'cycles': [],
            'functions': None,
            'address': '',
            'cpu_name': '',
            'os': ''}

    info = {}
    queries = []

    for uuid in utils.get_sample(uuids, fraction):
        data = base.copy()
        info[uuid] = data
        queries.append(Query(socorro.ProcessedCrash.URL, params={'crash_id': uuid}, handler=handler, handlerdata=data))

    socorro.ProcessedCrash(queries=queries).wait()

    return info


def __cycles_detection(funs):
    """Detect if there are some cycle in the backtrace [a,b,c,d,b,c,d,b,c,d...]

    Args:
        funs (List[str]): functions list

    Returns:
        list: the different cycles present in the backtrace
    """

    # TODO: improve this algorithm (not sure that's a good one)
    positions = {}
    # we get the function positions in the trace
    for i in range(len(funs)):
        fun = funs[i]
        if fun in positions:
            positions[fun].append(i)
        else:
            positions[fun] = [i]

    lengths = {}
    for k, v in positions.items():
        if len(v) >= 2:
            l = v[1] - v[0]
            good = True
            for i in range(2, len(v)):
                if v[i] - v[i - 1] != l:
                    good = False
                    break
            if good:
                if l in lengths:
                    lengths[l].append((k, v))
                else:
                    lengths[l] = [(k, v)]

    cycles = []
    for k, v in lengths.items():
        l = sorted(v, key=lambda x: x[1][0])
        pat = []
        container = [l[0][0]]
        pos = l[0][1][0]
        for i in range(1, len(l)):
            _pos = l[i][1][0]
            if _pos == pos + 1:
                container.append(l[i][0])
                pos = _pos
            else:
                pat.append(tuple(container))
                container = [l[i][0]]
                pos = _pos

        pat.append(tuple(container))
        cycles += pat

    cycles = tuple(cycles)

    return cycles
