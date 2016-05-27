# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from clouseau import bugzilla


class BugIDTest(unittest.TestCase):

    def test_bugid(self):

        def bughandler(bug, data):
            data.update(bug)

        bug = {}
        bugzilla.Bugzilla(12345, bughandler=bughandler, bugdata=bug).get_data().wait()

        self.assertEqual(bug['id'], 12345)
        self.assertEqual(bug['resolution'], u'FIXED')
        self.assertEqual(bug['assigned_to'], u'jefft@formerly-netscape.com.tld')
        self.assertEqual(bug['summary'], u'[DOGFOOD] Unable to Forward a message received as an Inline page or an attachment')

    def test_bugids(self):

        def bughandler(bug, data):
            data[bug['id']] = bug

        bugs = {}
        bugzilla.Bugzilla([12345, 12346], bughandler=bughandler, bugdata=bugs).get_data().wait()

        self.assertEqual(bugs[12345]['id'], 12345)
        self.assertEqual(bugs[12345]['resolution'], u'FIXED')
        self.assertEqual(bugs[12345]['assigned_to'], u'jefft@formerly-netscape.com.tld')
        self.assertEqual(bugs[12345]['summary'], u'[DOGFOOD] Unable to Forward a message received as an Inline page or an attachment')

        self.assertEqual(bugs[12346]['id'], 12346)
        self.assertEqual(bugs[12346]['resolution'], u'FIXED')
        self.assertEqual(bugs[12346]['assigned_to'], u'dougt@mozilla.com')
        self.assertEqual(bugs[12346]['summary'], u'nsOutputFileStream should buffer the output')

    def test_search(self):

        def bughandler(bug, data):
            data[bug['id']] = bug

        bugs = {}
        bugzilla.Bugzilla('bug_id=12345%2C12346&bug_id_type=anyexact&list_id=12958345&resolution=FIXED&query_format=advanced', bughandler=bughandler, bugdata=bugs).get_data().wait()

        self.assertEqual(bugs[12345]['id'], 12345)
        self.assertEqual(bugs[12346]['id'], 12346)

    def test_search_multiple(self):

        def bughandler(bug, data):
            data[bug['id']] = bug

        bugs = {}
        bugzilla.Bugzilla(['bug_id=12345%2C12346%2C12347', 'bug_id=12348%2C12349%2C12350'], bughandler=bughandler, bugdata=bugs).get_data().wait()

        self.assertEqual(bugs[12345]['id'], 12345)
        self.assertEqual(bugs[12346]['id'], 12346)
        self.assertEqual(bugs[12347]['id'], 12347)
        self.assertEqual(bugs[12348]['id'], 12348)
        self.assertEqual(bugs[12349]['id'], 12349)
        self.assertEqual(bugs[12350]['id'], 12350)


class BugCommentHistoryTest(unittest.TestCase):

    def test_bugid(self):

        def bughandler(bug, data):
            data['bug'] = bug

        def commenthandler(bug, bugid, data):
            data['comment'] = bug['comments']

        def historyhandler(bug, data):
            data['history'] = bug

        data = {}
        bugzilla.Bugzilla(12345, bughandler=bughandler, bugdata=data, commenthandler=commenthandler, commentdata=data, historyhandler=historyhandler, historydata=data).get_data().wait()

        self.assertEqual(data['bug']['id'], 12345)
        self.assertEqual(len(data['comment']), 19)
        self.assertTrue(data['comment'][0]['text'].startswith(u'Steps to reproduce'))
        self.assertEqual(len(data['history']['history']), 24)


class BugAttachmentTest(unittest.TestCase):

    def test_bugid(self):

        def bughandler(bug, data):
            data['bug'] = bug

        def commenthandler(bug, bugid, data):
            data['comment'] = bug['comments']

        def historyhandler(bug, data):
            data['history'] = bug

        def attachmenthandler(bug, bugid, data):
            data['attachment'] = bug

        data = {}
        bugzilla.Bugzilla(12345, bughandler=bughandler, bugdata=data, commenthandler=commenthandler, commentdata=data, historyhandler=historyhandler, historydata=data, attachmenthandler=attachmenthandler, attachmentdata=data).get_data().wait()

        self.assertEqual(data['bug']['id'], 12345)
        self.assertEqual(len(data['comment']), 19)
        self.assertTrue(data['comment'][0]['text'].startswith(u'Steps to reproduce'))
        self.assertEqual(len(data['history']['history']), 24)
        self.assertEqual(len(data['attachment']), 1)
        self.assertEqual(data['attachment'][0]['description'], 'Some patch.')
        self.assertEqual(data['attachment'][0]['is_patch'], 1)
        self.assertEqual(data['attachment'][0]['is_obsolete'], 1)


if __name__ == '__main__':
    unittest.main()
