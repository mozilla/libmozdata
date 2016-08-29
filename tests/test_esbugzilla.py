# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from libmozdata.esbugzilla import ESBugzilla


class BugHistoryTest(unittest.TestCase):
    def test_history(self):
        history = ESBugzilla().get_bug_history(12345)
        self.assertEqual(len(history['hits']['hits']), 26)
        last_change = history['hits']['hits'][-1]['_source']['changes'][0]
        self.assertEqual(last_change['field_name'], 'attachments.isobsolete')
        self.assertEqual(last_change['new_value'], '1')
        self.assertEqual(last_change['old_value'], '0')

    def test_comments(self):
        comments = ESBugzilla().get_bug_comments(12345)
        self.assertEqual(comments['hits']['hits'][-1]['_source']['comment'], 'Oops, sorry.')
