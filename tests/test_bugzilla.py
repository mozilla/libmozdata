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

    def test_search(self):
        def bughandler(bug, data):
            data['bug'] = bug

        def commenthandler(bug, bugid, data):
            data['comment'] = bug['comments']

        def historyhandler(bug, data):
            data['history'] = bug

        data = {}
        bugzilla.Bugzilla('bug_id=12345', bughandler=bughandler, bugdata=data, commenthandler=commenthandler, commentdata=data, historyhandler=historyhandler, historydata=data).get_data().wait()

        self.assertEqual(data['bug']['id'], 12345)
        self.assertEqual(len(data['comment']), 19)
        self.assertTrue(data['comment'][0]['text'].startswith(u'Steps to reproduce'))
        self.assertEqual(len(data['history']['history']), 24)

    def test_search_history(self):
        def bughandler(bug, data):
            data['bug'] = bug

        def commenthandler(bug, bugid, data):
            data['comment'] = bug['comments']

        def historyhandler(bug, data):
            data['history'] = bug['history']

        data = {}
        bugzilla.Bugzilla(12345, bughandler=bughandler, bugdata=data, commenthandler=commenthandler, commentdata=data, historyhandler=historyhandler, historydata=data).get_data().wait()

        all = bugzilla.Bugzilla.get_history_matches(data['history'], {})
        self.assertEqual(len(all), len(data['history']))

        change_to_assigned = bugzilla.Bugzilla.get_history_matches(data['history'], {'added': 'ASSIGNED'})
        self.assertEqual(change_to_assigned, [{'when': '1999-08-29T17:43:15Z', 'changes': [{'added': 'ASSIGNED', 'field_name': 'status', 'removed': 'NEW'}], 'who': 'jefft@formerly-netscape.com.tld'}])

        blocks_changes = bugzilla.Bugzilla.get_history_matches(data['history'], {'field_name': 'blocks'})
        self.assertEqual(blocks_changes, [{'changes': [{'removed': '', 'added': '11091', 'field_name': 'blocks'}], 'who': 'lchiang@formerly-netscape.com.tld', 'when': '1999-09-20T22:58:39Z'}, {'changes': [{'removed': '', 'added': '17976', 'field_name': 'blocks'}], 'who': 'chofmann@gmail.com', 'when': '1999-11-04T14:05:18Z'}])

        single_block_change = bugzilla.Bugzilla.get_history_matches(data['history'], {'added': '11091', 'field_name': 'blocks'})
        self.assertEqual(single_block_change, [{'changes': [{'removed': '', 'added': '11091', 'field_name': 'blocks'}], 'who': 'lchiang@formerly-netscape.com.tld', 'when': '1999-09-20T22:58:39Z'}])


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

    def test_search(self):
        def bughandler(bug, data):
            data['bug'] = bug

        def commenthandler(bug, bugid, data):
            data['comment'] = bug['comments']

        def historyhandler(bug, data):
            data['history'] = bug

        def attachmenthandler(bug, bugid, data):
            data['attachment'] = bug

        data = {}
        bugzilla.Bugzilla('bug_id=12345', bughandler=bughandler, bugdata=data, commenthandler=commenthandler, commentdata=data, historyhandler=historyhandler, historydata=data, attachmenthandler=attachmenthandler, attachmentdata=data).get_data().wait()

        self.assertEqual(data['bug']['id'], 12345)
        self.assertEqual(len(data['comment']), 19)
        self.assertTrue(data['comment'][0]['text'].startswith(u'Steps to reproduce'))
        self.assertEqual(len(data['history']['history']), 24)
        self.assertEqual(len(data['attachment']), 1)
        self.assertEqual(data['attachment'][0]['description'], 'Some patch.')
        self.assertEqual(data['attachment'][0]['is_patch'], 1)
        self.assertEqual(data['attachment'][0]['is_obsolete'], 1)


class BugDuplicateTest(unittest.TestCase):

    def test_duplicate(self):
        self.assertEqual(bugzilla.Bugzilla.follow_dup([1244129, 890156]), {'1244129': '1240533', '890156': None})

    def test_double_duplicate(self):
        self.assertEqual(bugzilla.Bugzilla.follow_dup([784349]), {'784349': '784345'})

    def test_not_duplicate(self):
        self.assertEqual(bugzilla.Bugzilla.follow_dup([890156, 1240533]), {'1240533': None, '890156': None})

if __name__ == '__main__':
    unittest.main()
