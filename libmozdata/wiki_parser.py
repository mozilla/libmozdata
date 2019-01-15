# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

try:
    from HTMLParser import HTMLParser
except:  # NOQA
    from html.parser import HTMLParser


class InvalidWiki(Exception):
    def __init__(self, s):
        super(InvalidWiki, self).__init__(s)


class WikiParser(HTMLParser):
    def __init__(self, tables=[0]):
        HTMLParser.__init__(self)
        self.tables = []
        self.rows = None
        self.td = None
        self.th = None
        self.table_counter = -1
        self.tables_number = set(tables)

    def feed(self, data):
        if not isinstance(data, str):
            data = str(data, 'ascii')
        HTMLParser.feed(self, data)

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.table_counter += 1
            if self.table_counter in self.tables_number:
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
                self.tables.append(self.rows)
                self.rows = None
                if self.table_counter == max(self.tables_number):
                    raise StopIteration()
            elif tag == 'td':
                self.rows[-1].append(self.td)
                self.td = None
            elif tag == 'th':
                self.rows[-1].append(self.th)
                self.th = None

    def handle_data(self, data):
        data = data.strip()
        if self.td is not None:
            self.td += data
        elif self.th is not None:
            self.th += data

    def get_tables(self):
        return self.tables
