# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import requests
from requests.exceptions import HTTPError

from . import config, utils
from .wiki_parser import InvalidWiki, WikiParser

OWNERS_URL = "https://wiki.mozilla.org/Release_Management/Release_owners"
_OWNERS = None


def _get_sub_versions(s):
    s = s.strip()
    s = s.split(".")
    return [int(v.split(" ", 1)[0]) for v in s]


def get_versions(s):
    fx = "Firefox "
    if not s.startswith(fx):
        raise InvalidWiki('Invalid version format, expect: "Firefox ..."')
    N = len(fx)
    version = s[N:]
    versions = version.split(";")
    return [_get_sub_versions(v) for v in versions]


def _get_list_people(s):
    return [x.strip() for x in s.split(",")]


def get_owners():
    global _OWNERS
    if _OWNERS is not None:
        return _OWNERS

    resp = requests.get(
        OWNERS_URL,
        headers={"User-Agent": config.get("User-Agent", "name", required=True)},
    )
    try:
        resp.raise_for_status()
    except HTTPError as e:
        raise InvalidWiki("Failed to load wiki data") from e

    html = resp.text.encode("ascii", errors="ignore")

    parser = WikiParser(tables=[0])
    try:
        parser.feed(html)
    except StopIteration:
        table = parser.get_tables()[0]
        if [
            "Firefox Version",
            "Owner",
            "Secondary",
            "Engineering REO",
            "Release Duty",
            "Corresponding ESR",
            "Release Date",
        ] != table[0]:
            raise InvalidWiki("Column headers are wrong")

        _OWNERS = []
        for row in table[1:]:
            try:
                # sometimes the date is 2019-XX-XX (when the date is not known)
                release_date = utils.get_date_ymd(row[6])
            except (AssertionError, ValueError):
                continue

            _OWNERS.append(
                {
                    "version": get_versions(row[0])[0][0],
                    "owner": row[1],
                    "secondary": row[2],
                    "engineering reo": row[3],
                    "release duty": _get_list_people(row[4]),
                    "corresponding esr": row[5],
                    "release date": release_date,
                }
            )
        return _OWNERS
