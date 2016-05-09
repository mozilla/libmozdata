# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import requests


__versions = None


def __getTemplateValue(url):
    """Get version value from html file

    Args:
        url (str): the url of the html file

    Returns:
        int: the version number
    """
    version_regex = re.compile(".*<p>(.*)</p>.*")
    template_page = str(requests.get(url).text.encode('utf-8')).replace('\n', '')
    parsed_template = version_regex.match(template_page)
    n = parsed_template.groups()[0]
    if n.endswith('\\n'):
        n = n[:-2]
    return int(n)


def __getVersions():
    """Get the versions number for each channel

    Returns:
        dict: versions for each channel
    """
    base_url = 'https://wiki.mozilla.org/Template:%s_VERSION'
    names = ['RELEASE', 'BETA', 'AURORA', 'CENTRAL']
    versions = list(map(lambda name: __getTemplateValue(base_url % name), names))
    return {'release': versions[0], 'beta': versions[1], 'aurora': versions[2], 'nightly': versions[3]}


def get():
    """Get current version number by channel

    Returns:
        dict: containing version by channel
    """
    global __versions
    if not __versions:
        __versions = __getVersions()

    return __versions
