# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from datetime import datetime
import dateutil.parser

try:
    from HTMLParser import HTMLParser
except:  # NOQA
    from html.parser import HTMLParser
import pytz
import requests


CALENDAR_URL = 'https://wiki.mozilla.org/Release_Management/Calendar'
_CALENDAR = None


class InvalidWiki(Exception):
    def __init__(self, s):
        super(InvalidWiki, self).__init__(s)


class CalendarParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.rows = None
        self.td = None
        self.th = None

    def handle_starttag(self, tag, attrs):
        if self.rows is None and tag == 'table':
            self.rows = []
        if self.rows is not None:
            if tag == 'tr':
                self.rows.append([])
            elif tag == 'td':
                self.td = ''
            elif tag == 'th':
                self.th = ''

    def handle_endtag(self, tag):
        if self.rows is not None:
            if tag == 'table':
                raise StopIteration()
            elif tag == 'td':
                self.rows[-1].append(self.td)
                self.td = None
            elif tag == 'th':
                self.rows[-1].append(self.th)
                self.th = None

    def handle_data(self, data):
        data = data.replace('\\n', '\n')
        data = data.strip()
        if self.td is not None:
            self.td = data
        elif self.th is not None:
            self.th = data

    @staticmethod
    def _get_date(s):
        return pytz.utc.localize(dateutil.parser.parse(s))

    @staticmethod
    def _get_sub_versions(s):
        s = s.split('.')
        return list(map(int, s))

    @staticmethod
    def _get_versions(s):
        fx = 'Firefox '
        if not s.startswith(fx):
            raise InvalidWiki('Invalid version format, expect: \"Firefox ...\"')
        version = s[len(fx):]
        versions = version.split(';')
        versions = list(map(CalendarParser._get_sub_versions, versions))
        return versions


def get_calendar():
    global _CALENDAR
    if _CALENDAR is not None:
        return _CALENDAR

    html = str(requests.get(CALENDAR_URL).text.encode('utf-8'))
    parser = CalendarParser()
    try:
        parser.feed(html)
    except StopIteration:
        if [
            'Quarter',
            'Soft Freeze',
            'Merge Date',
            'Central',
            'Beta',
            'Release Date',
            'Release',
            'ESR',
        ] != parser.rows[0]:
            raise InvalidWiki('Column headers are wrong')

        _CALENDAR = []
        for row in parser.rows[1:]:
            if row[0].startswith('Q'):
                row = row[1:]
            _CALENDAR.append(
                {
                    'soft freeze': CalendarParser._get_date(row[0]),
                    'merge': CalendarParser._get_date(row[1]),
                    'central': CalendarParser._get_versions(row[2])[0][0],
                    'beta': CalendarParser._get_versions(row[3])[0][0],
                    'release date': CalendarParser._get_date(row[4]),
                    'release': CalendarParser._get_versions(row[5])[0][0],
                    'esr': CalendarParser._get_versions(row[6]),
                }
            )
        return _CALENDAR


def get_next_release_date():
    cal = get_calendar()
    now = pytz.utc.localize(datetime.utcnow())
    for c in cal:
        if now < c['release date']:
            return c['release date']
    return None
