# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import os
from libmozdata import bugzilla
import responses
from tests.auto_mock import MockTestCase


class BugIDTest(MockTestCase):

    mock_urls = [
        bugzilla.Bugzilla.URL,
    ]

    @responses.activate
    def test_bugid(self):

        def bughandler(bug, data):
            data.update(bug)

        bug = {}
        bugzilla.Bugzilla(12345, bughandler=bughandler, bugdata=bug).get_data().wait()

        self.assertEqual(bug['id'], 12345)
        self.assertEqual(bug['resolution'], u'FIXED')
        self.assertEqual(bug['assigned_to'], u'jefft@formerly-netscape.com.tld')
        self.assertEqual(bug['summary'], u'[DOGFOOD] Unable to Forward a message received as an Inline page or an attachment')

    @responses.activate
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

    @responses.activate
    def test_search(self):

        def bughandler(bug, data):
            data[bug['id']] = bug

        bugs = {}

        bugzilla.Bugzilla('bug_id=12345%2C12346&bug_id_type=anyexact&list_id=12958345&resolution=FIXED&query_format=advanced', bughandler=bughandler, bugdata=bugs).get_data().wait()

        self.assertEqual(bugs[12345]['id'], 12345)
        self.assertEqual(bugs[12346]['id'], 12346)

    @responses.activate
    def test_search_dict(self):

        def bughandler(bug, data):
            data[bug['id']] = bug

        bugs = {}

        # Unique bug id
        terms = {
            'bug_id': 12345,
            'bug_id_type': 'anyexact',
            'list_id': 12958345,
            'resolution': 'FIXED',
            'query_format': 'advanced',
        }
        bugzilla.Bugzilla(terms, bughandler=bughandler, bugdata=bugs).get_data().wait()

        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[12345]['id'], 12345)

        bugs = {}

        # Mutiple bugs
        terms = {
            'bug_id': [12345, 12346],
            'bug_id_type': 'anyexact',
            'list_id': 12958345,
            'resolution': 'FIXED',
            'query_format': 'advanced',
        }
        bugzilla.Bugzilla(terms, bughandler=bughandler, bugdata=bugs).get_data().wait()

        self.assertEqual(len(bugs), 2)
        self.assertEqual(bugs[12345]['id'], 12345)
        self.assertEqual(bugs[12346]['id'], 12346)

        bugs = {}

        # Mutiple queries
        terms = [
            {
                'bug_id': 12345,
            },
            {
                'bug_id': 12346,
            },
        ]
        bugzilla.Bugzilla(terms, bughandler=bughandler, bugdata=bugs).get_data().wait()

        self.assertEqual(len(bugs), 2)
        self.assertEqual(bugs[12345]['id'], 12345)
        self.assertEqual(bugs[12346]['id'], 12346)

    @responses.activate
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


class BugCommentHistoryTest(MockTestCase):

    mock_urls = [
        bugzilla.Bugzilla.URL,
    ]

    @responses.activate
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

    @responses.activate
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

    @responses.activate
    def test_search_history(self):
        def historyhandler(bug, data):
            data['history'] = bug['history']

        data = {}
        bugzilla.Bugzilla(12345, historyhandler=historyhandler, historydata=data).get_data().wait()

        all = bugzilla.Bugzilla.get_history_matches(data['history'], {})
        self.assertEqual(len(all), len(data['history']))

        change_to_assigned = bugzilla.Bugzilla.get_history_matches(data['history'], {'added': 'ASSIGNED'})
        self.assertEqual(change_to_assigned, [{'when': '1999-08-29T17:43:15Z', 'changes': [{'added': 'ASSIGNED', 'field_name': 'status', 'removed': 'NEW'}], 'who': 'jefft@formerly-netscape.com.tld'}])

        blocks_changes = bugzilla.Bugzilla.get_history_matches(data['history'], {'field_name': 'blocks'})
        self.assertEqual(blocks_changes, [{'changes': [{'removed': '', 'added': '11091', 'field_name': 'blocks'}], 'who': 'lchiang@formerly-netscape.com.tld', 'when': '1999-09-20T22:58:39Z'}, {'changes': [{'removed': '', 'added': '17976', 'field_name': 'blocks'}], 'who': 'chofmann@gmail.com', 'when': '1999-11-04T14:05:18Z'}])

        single_block_change = bugzilla.Bugzilla.get_history_matches(data['history'], {'added': '11091', 'field_name': 'blocks'})
        self.assertEqual(single_block_change, [{'changes': [{'removed': '', 'added': '11091', 'field_name': 'blocks'}], 'who': 'lchiang@formerly-netscape.com.tld', 'when': '1999-09-20T22:58:39Z'}])

        data = {}
        bugzilla.Bugzilla(1005958, historyhandler=historyhandler, historydata=data).get_data().wait()

        multiple_changes = bugzilla.Bugzilla.get_history_matches(data['history'], {'added': 'approval-mozilla-release?'})
        self.assertEqual(multiple_changes, [{'changes': [{'added': 'approval-mozilla-aurora?, approval-mozilla-beta?, approval-mozilla-release?', 'attachment_id': 8417443, 'field_name': 'flagtypes.name', 'removed': ''}], 'when': '2014-05-05T20:25:06Z', 'who': 'hurley@todesschaf.org'}])

    @responses.activate
    def test_search_landing(self):
        def commenthandler(bug, bugid, data):
            data['comments'] = bug['comments']

        data = {}
        bugzilla.Bugzilla(538189, commenthandler=commenthandler, commentdata=data).get_data().wait()

        inbound = bugzilla.Bugzilla.get_landing_comments(data['comments'], 'inbound')
        self.assertEqual(len(inbound), 1)
        self.assertEqual(inbound[0]['revision'], '42c54c7cb4a3')
        self.assertEqual(inbound[0]['comment'], {'attachment_id': None, 'raw_text': 'http://hg.mozilla.org/integration/mozilla-inbound/rev/42c54c7cb4a3', 'tags': [], 'is_private': False, 'creator': 'cam@mcc.id.au', 'bug_id': 538189, 'author': 'cam@mcc.id.au', 'text': 'http://hg.mozilla.org/integration/mozilla-inbound/rev/42c54c7cb4a3', 'id': 5655196, 'creation_time': '2011-08-15T21:21:13Z', 'time': '2011-08-15T21:21:13Z'})
        central = bugzilla.Bugzilla.get_landing_comments(data['comments'], 'central')
        self.assertEqual(len(central), 1)
        self.assertEqual(central[0]['revision'], '42c54c7cb4a3')
        self.assertEqual(central[0]['comment'], {'attachment_id': None, 'raw_text': 'http://hg.mozilla.org/mozilla-central/rev/42c54c7cb4a3\n\nAsa, did you mean to set approval-beta+ instead of approval-beta?', 'tags': [], 'is_private': False, 'creator': 'khuey@kylehuey.com', 'bug_id': 538189, 'author': 'khuey@kylehuey.com', 'text': 'http://hg.mozilla.org/mozilla-central/rev/42c54c7cb4a3\n\nAsa, did you mean to set approval-beta+ instead of approval-beta?', 'id': 5656549, 'creation_time': '2011-08-16T11:02:36Z', 'time': '2011-08-16T11:02:36Z'})
        beta = bugzilla.Bugzilla.get_landing_comments(data['comments'], 'beta')
        self.assertEqual(len(beta), 1)
        self.assertEqual(beta[0]['revision'], '1d02edaa92bc')
        self.assertEqual(beta[0]['comment'], {'attachment_id': None, 'raw_text': 'http://hg.mozilla.org/releases/mozilla-beta/rev/1d02edaa92bc', 'tags': [], 'is_private': False, 'creator': 'cam@mcc.id.au', 'bug_id': 538189, 'author': 'cam@mcc.id.au', 'text': 'http://hg.mozilla.org/releases/mozilla-beta/rev/1d02edaa92bc', 'id': 5686198, 'creation_time': '2011-08-29T21:55:57Z', 'time': '2011-08-29T21:55:57Z'})

        multiple = bugzilla.Bugzilla.get_landing_comments(data['comments'], ['beta', 'inbound', 'central'])
        self.assertEqual(multiple, [{'revision': '42c54c7cb4a3', 'channel': 'inbound', 'comment': {'creation_time': '2011-08-15T21:21:13Z', 'is_private': False, 'attachment_id': None, 'text': 'http://hg.mozilla.org/integration/mozilla-inbound/rev/42c54c7cb4a3', 'creator': 'cam@mcc.id.au', 'tags': [], 'bug_id': 538189, 'author': 'cam@mcc.id.au', 'time': '2011-08-15T21:21:13Z', 'id': 5655196, 'raw_text': 'http://hg.mozilla.org/integration/mozilla-inbound/rev/42c54c7cb4a3'}}, {'revision': '42c54c7cb4a3', 'channel': 'central', 'comment': {'creation_time': '2011-08-16T11:02:36Z', 'is_private': False, 'attachment_id': None, 'text': 'http://hg.mozilla.org/mozilla-central/rev/42c54c7cb4a3\n\nAsa, did you mean to set approval-beta+ instead of approval-beta?', 'creator': 'khuey@kylehuey.com', 'tags': [], 'bug_id': 538189, 'author': 'khuey@kylehuey.com', 'time': '2011-08-16T11:02:36Z', 'id': 5656549, 'raw_text': 'http://hg.mozilla.org/mozilla-central/rev/42c54c7cb4a3\n\nAsa, did you mean to set approval-beta+ instead of approval-beta?'}}, {'revision': '1d02edaa92bc', 'channel': 'beta', 'comment': {'creation_time': '2011-08-29T21:55:57Z', 'is_private': False, 'attachment_id': None, 'text': 'http://hg.mozilla.org/releases/mozilla-beta/rev/1d02edaa92bc', 'creator': 'cam@mcc.id.au', 'tags': [], 'bug_id': 538189, 'author': 'cam@mcc.id.au', 'time': '2011-08-29T21:55:57Z', 'id': 5686198, 'raw_text': 'http://hg.mozilla.org/releases/mozilla-beta/rev/1d02edaa92bc'}}])

        data = {}
        bugzilla.Bugzilla(679352, commenthandler=commenthandler, commentdata=data).get_data().wait()

        central = bugzilla.Bugzilla.get_landing_comments(data['comments'], 'central')
        self.assertEqual(len(central), 8)


class BugAttachmentTest(MockTestCase):

    mock_urls = [
        bugzilla.Bugzilla.URL,
    ]

    @responses.activate
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

    @responses.activate
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

    @responses.activate
    def test_search_only_attachment(self):
        def bughandler(bug, data):
            data['bug'] = bug

        def attachmenthandler(bug, bugid, data):
            data['attachment'] = bug

        data = {}
        bugzilla.Bugzilla('bug_id=12345', bughandler=bughandler, bugdata=data, attachmenthandler=attachmenthandler, attachmentdata=data).get_data().wait()

        self.assertEqual(data['bug']['id'], 12345)
        self.assertEqual(len(data['attachment']), 1)
        self.assertEqual(data['attachment'][0]['description'], 'Some patch.')
        self.assertEqual(data['attachment'][0]['is_patch'], 1)
        self.assertEqual(data['attachment'][0]['is_obsolete'], 1)

    @responses.activate
    def test_include_fields(self):
        def attachmenthandler(bug, bugid, data):
            data['attachment'] = bug

        data = {}
        bugzilla.Bugzilla(12345, attachmenthandler=attachmenthandler, attachmentdata=data, attachment_include_fields=['description']).get_data().wait()

        self.assertEqual(data['attachment'][0]['description'], 'Some patch.')
        self.assertNotIn('is_patch', data['attachment'][0])
        self.assertNotIn('is_obsolete', data['attachment'][0])


class BugDuplicateTest(MockTestCase):

    mock_urls = [
        bugzilla.Bugzilla.URL,
    ]

    @responses.activate
    def test_duplicate(self):
        self.assertEqual(bugzilla.Bugzilla.follow_dup([1244129, 890156]), {'1244129': '1240533', '890156': None})

    @responses.activate
    def test_double_duplicate(self):
        self.assertEqual(bugzilla.Bugzilla.follow_dup([784349]), {'784349': '784345'})

    @responses.activate
    def test_not_duplicate(self):
        self.assertEqual(bugzilla.Bugzilla.follow_dup([890156, 1240533]), {'1240533': None, '890156': None})


class User(MockTestCase):

    mock_urls = [
        bugzilla.BugzillaUser.URL,
    ]

    def __init__(self, a):
        tok = os.environ.get('API_KEY_BUGZILLA')
        if tok:
            bugzilla.BugzillaUser.TOKEN = tok
        super(User, self).__init__(a)

    @responses.activate
    def test_get_user(self):
        user = {}
        user_data = {}

        def user_handler(u, data):
            user.update(u)
            data.update(u)

        bugzilla.BugzillaUser(user_names='nobody@mozilla.org', user_handler=user_handler, user_data=user_data).wait()

        self.assertEqual(user['email'], 'nobody@mozilla.org')
        self.assertEqual(user['name'], 'nobody@mozilla.org')
        self.assertEqual(user['real_name'], 'Nobody; OK to take it and work on it')
        self.assertEqual(user, user_data)

    @responses.activate
    def test_get_user_include_fields(self):
        user = {}
        user_data = {}

        def user_handler(u, data):
            user.update(u)
            data.update(u)

        bugzilla.BugzillaUser(user_names='nobody@mozilla.org', include_fields=['email', 'real_name'], user_handler=user_handler, user_data=user_data).wait()

        self.assertEqual(user['email'], 'nobody@mozilla.org')
        self.assertEqual(user['real_name'], 'Nobody; OK to take it and work on it')
        self.assertNotIn('name', user)
        self.assertNotIn('id', user)
        self.assertEqual(user, user_data)

    @responses.activate
    def test_get_user_no_data(self):
        user = {}

        def user_handler(u):
            user.update(u)

        bugzilla.BugzillaUser(user_names='nobody@mozilla.org', user_handler=user_handler).wait()

        self.assertEqual(user['email'], 'nobody@mozilla.org')
        self.assertEqual(user['name'], 'nobody@mozilla.org')
        self.assertEqual(user['real_name'], 'Nobody; OK to take it and work on it')

    @responses.activate
    def test_get_user_id(self):
        user = {}

        def user_handler(u):
            user.update(u)

        bugzilla.BugzillaUser(user_names=1, user_handler=user_handler).wait()

        self.assertEqual(user['email'], 'nobody@mozilla.org')
        self.assertEqual(user['name'], 'nobody@mozilla.org')
        self.assertEqual(user['real_name'], 'Nobody; OK to take it and work on it')

    @responses.activate
    def test_get_user_id_string(self):
        user = {}

        def user_handler(u):
            user.update(u)

        bugzilla.BugzillaUser(user_names='1', user_handler=user_handler).wait()

        self.assertEqual(user['email'], 'nobody@mozilla.org')
        self.assertEqual(user['name'], 'nobody@mozilla.org')
        self.assertEqual(user['real_name'], 'Nobody; OK to take it and work on it')

    @responses.activate
    def test_get_user_array(self):
        user = {}

        def user_handler(u):
            user.update(u)

        bugzilla.BugzillaUser(user_names=['nobody@mozilla.org'], user_handler=user_handler).wait()

        self.assertEqual(user['email'], 'nobody@mozilla.org')
        self.assertEqual(user['name'], 'nobody@mozilla.org')
        self.assertEqual(user['real_name'], 'Nobody; OK to take it and work on it')

    @responses.activate
    def test_get_users(self):
        user = {
            'first': {},
            'second': {},
        }

        def user_handler(u):
            if u['id'] == 1:
                user['first'].update(u)
            elif u['id'] == 208267:
                user['second'].update(u)
            else:
                raise Exception('Unexpected ID')

        bugzilla.BugzillaUser(user_names=['nobody@mozilla.org', 'bugbot@bugzilla.org'], user_handler=user_handler).wait()

        self.assertEqual(user['first']['email'], 'nobody@mozilla.org')
        self.assertEqual(user['first']['name'], 'nobody@mozilla.org')
        self.assertEqual(user['first']['real_name'], 'Nobody; OK to take it and work on it')
        self.assertEqual(user['second']['email'], 'bugbot@bugzilla.org')
        self.assertEqual(user['second']['name'], 'bugbot@bugzilla.org')
        self.assertEqual(user['second']['real_name'], 'bugbot on irc.mozilla.org')

    @responses.activate
    def test_get_users_ids(self):
        user = {
            'first': {},
            'second': {},
        }

        def user_handler(u):
            if u['id'] == 1:
                user['first'].update(u)
            elif u['id'] == 208267:
                user['second'].update(u)
            else:
                raise Exception('Unexpected ID')

        bugzilla.BugzillaUser(user_names=['1', 208267], user_handler=user_handler).wait()

        self.assertEqual(user['first']['email'], 'nobody@mozilla.org')
        self.assertEqual(user['first']['name'], 'nobody@mozilla.org')
        self.assertEqual(user['first']['real_name'], 'Nobody; OK to take it and work on it')
        self.assertEqual(user['second']['email'], 'bugbot@bugzilla.org')
        self.assertEqual(user['second']['name'], 'bugbot@bugzilla.org')
        self.assertEqual(user['second']['real_name'], 'bugbot on irc.mozilla.org')

    @responses.activate
    def test_search_single_result(self):
        user = {}

        def user_handler(u):
            user.update(u)

        bugzilla.BugzillaUser(search_strings='match=nobody@mozilla.org', user_handler=user_handler).wait()

        self.assertEqual(user['email'], 'nobody@mozilla.org')
        self.assertEqual(user['name'], 'nobody@mozilla.org')
        self.assertEqual(user['real_name'], 'Nobody; OK to take it and work on it')

    @responses.activate
    def test_search_multiple_results(self):
        users = []

        def user_handler(u):
            users.append(u)

        bugzilla.BugzillaUser(search_strings='match=nobody', user_handler=user_handler).wait()

        foundNobody1 = False
        foundNobody2 = False
        for user in users:
            if user['email'] == 'nobody@mozilla.org':
                self.assertFalse(foundNobody1)
                foundNobody1 = True
                self.assertEqual(user['name'], 'nobody@mozilla.org')
                self.assertEqual(user['real_name'], 'Nobody; OK to take it and work on it')
            elif user['email'] == 'attach-and-request@bugzilla.bugs':
                self.assertFalse(foundNobody2)
                foundNobody2 = True
                self.assertEqual(user['name'], 'attach-and-request@bugzilla.bugs')
                self.assertEqual(user['real_name'], 'Nobody; OK to take it and work on it')

        self.assertTrue(foundNobody1)
        self.assertTrue(foundNobody2)

    @responses.activate
    def test_search_multiple_queries(self):
        users = []

        def user_handler(u):
            users.append(u)

        bugzilla.BugzillaUser(search_strings=['match=nobody@mozilla.org', 'match=attach-and-request@bugzilla.bugs'], user_handler=user_handler).wait()

        foundNobody1 = False
        foundNobody2 = False
        for user in users:
            if user['email'] == 'nobody@mozilla.org':
                self.assertFalse(foundNobody1)
                foundNobody1 = True
                self.assertEqual(user['name'], 'nobody@mozilla.org')
                self.assertEqual(user['real_name'], 'Nobody; OK to take it and work on it')
            elif user['email'] == 'attach-and-request@bugzilla.bugs':
                self.assertFalse(foundNobody2)
                foundNobody2 = True
                self.assertEqual(user['name'], 'attach-and-request@bugzilla.bugs')
                self.assertEqual(user['real_name'], 'Nobody; OK to take it and work on it')

        self.assertTrue(foundNobody1)
        self.assertTrue(foundNobody2)


if __name__ == '__main__':
    unittest.main()
