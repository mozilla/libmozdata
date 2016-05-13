# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

try:
    import urllib.request as ur
except ImportError:
    import urllib as ur

import json


__versions = None


def __get_major(v):
    return int(v.split('.')[0])


def __getVersions():
    """Get the versions number for each channel

    Returns:
        dict: versions for each channel
    """
    url = 'https://product-details.mozilla.org/firefox_versions.json'
    resp = ur.urlopen(url)
    data = json.loads(resp.read().decode('utf-8'))
    resp.close()
    aurora = data['FIREFOX_AURORA']
    nightly = '%d.0a1' % (__get_major(aurora) + 1)
    return {'release': data['LATEST_FIREFOX_VERSION'],
            'beta': data['LATEST_FIREFOX_RELEASED_DEVEL_VERSION'],
            'aurora': str(aurora),
            'nightly': nightly}


def get(base=False):
    """Get current version number by channel

    Returns:
        dict: containing version by channel
    """
    global __versions
    if not __versions:
        __versions = __getVersions()

    if base:
        res = {}
        for k, v in __versions.items():
            res[k] = __get_major(v)
        return res

    return __versions
