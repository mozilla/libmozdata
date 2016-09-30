# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import sys
import warnings
from datetime import timedelta
from libmozdata.bugzilla import Bugzilla
from libmozdata.socorro import Socorro
from libmozdata.hgmozilla import Mercurial
from libmozdata import patchanalysis
from libmozdata import utils
from tests.auto_mock import MockTestCase
import responses


class PatchAnalysisTest(MockTestCase):
    mock_urls = [
        Bugzilla.URL,
        Socorro.CRASH_STATS_URL,
        Mercurial.HG_URL,
    ]

    def assertWarnings(self, warnings, expected_warnings):
        missed_warnings = [ew for ew in expected_warnings if ew not in [str(w.message) for w in warnings]]

        for missed_warning in missed_warnings:
            print('Warning ("' + missed_warning + '") couldn\'t be found')

        unexpected_warnings = [str(w.message) for w in warnings if str(w.message) not in expected_warnings]

        for unexpected_warning in unexpected_warnings:
            print('Unexpected warning ("' + unexpected_warning + '") found')

        self.assertEqual(len(missed_warnings), 0)
        self.assertEqual(len(unexpected_warnings), 0)

    def assertDictEqual(self, d1, d2, msg=None):
        for k, v1 in d1.items():
            self.assertIn(k, d2, msg)
            self.assertEqual(v1, d2[k], msg)

        return True

    @responses.activate
    def test_bug_analysis(self):
        info = patchanalysis.bug_analysis(547914)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 1)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 11)
        self.assertEqual(info['patches']['1584ba8c1b86']['changes_size'], 640)
        self.assertEqual(info['patches']['1584ba8c1b86']['test_changes_size'], 0)
        self.assertEqual(info['patches']['1584ba8c1b86']['modules_num'], 1)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['patches']['1584ba8c1b86']['code_churn_overall'], 205)
        self.assertEqual(info['patches']['1584ba8c1b86']['code_churn_last_3_releases'], 36)
        self.assertEqual(info['patches']['1584ba8c1b86']['developer_familiarity_overall'], 13)
        self.assertEqual(info['patches']['1584ba8c1b86']['developer_familiarity_last_3_releases'], 1)
        self.assertEqual(info['patches']['1584ba8c1b86']['reviewer_familiarity_overall'], 0)
        self.assertEqual(info['patches']['1584ba8c1b86']['reviewer_familiarity_last_3_releases'], 0)
        self.assertIn('shaver@mozilla.org', info['users']['reviewers'])
        self.assertIn('gerv@mozilla.org', info['users']['reviewers'])
        self.assertEqual(info['users']['assignee']['email'], 'philringnalda@gmail.com')
        self.assertEqual(len(info['patches']), 1)
        self.assertEqual(info['patches']['1584ba8c1b86']['source'], 'mercurial')
        self.assertEqual(info['patches']['1584ba8c1b86']['url'], 'https://hg.mozilla.org/mozilla-central/rev/1584ba8c1b86')

        bug = {}

        def bughandler(found_bug, data):
            bug.update(found_bug)

        def commenthandler(found_bug, bugid, data):
            bug['comments'] = found_bug['comments']

        def historyhandler(found_bug, data):
            bug['history'] = found_bug['history']

        def attachmenthandler(attachments, bugid, data):
            bug['attachments'] = attachments

        Bugzilla('id=547914', bughandler=bughandler, commenthandler=commenthandler, attachmenthandler=attachmenthandler, historyhandler=historyhandler).get_data().wait()

        info2 = patchanalysis.bug_analysis(bug)
        self.assertEqual(info2, info)

        info = patchanalysis.bug_analysis(647570)
        self.assertEqual(info['backout_num'], 1)
        self.assertEqual(info['blocks'], 3)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 40)
        self.assertEqual(info['patches']['8641afbd20e6']['changes_size'], 486)
        self.assertEqual(info['patches']['8641afbd20e6']['test_changes_size'], 0)
        self.assertEqual(info['patches']['8641afbd20e6']['modules_num'], 3)
        self.assertEqual(info['r-ed_patches'], 3)
        self.assertEqual(info['patches']['8641afbd20e6']['code_churn_overall'], 184)
        self.assertEqual(info['patches']['8641afbd20e6']['code_churn_last_3_releases'], 31)
        self.assertEqual(info['patches']['8641afbd20e6']['developer_familiarity_overall'], 4)
        self.assertEqual(info['patches']['8641afbd20e6']['developer_familiarity_last_3_releases'], 4)
        self.assertEqual(info['patches']['8641afbd20e6']['reviewer_familiarity_overall'], 16)
        self.assertEqual(info['patches']['8641afbd20e6']['reviewer_familiarity_last_3_releases'], 0)
        self.assertEqual(len(info['patches']), 1)
        self.assertEqual(info['patches']['8641afbd20e6']['source'], 'mercurial')
        self.assertEqual(info['patches']['8641afbd20e6']['url'], 'https://hg.mozilla.org/mozilla-central/rev/8641afbd20e6')

        # Backed out once (when it was on inbound) with changesets from anther bug.
        # Author of the patch uses a different email in Bugzilla and Mercurial.
        # Reviewer's email doesn't start with his nick, but he's in CC list.
        with warnings.catch_warnings(record=True) as w:
            info = patchanalysis.bug_analysis(1271794)
            self.assertWarnings(w, ['Revision d0ab0d508a24 was not found.', 'Revision 9f4983dfd881 was not found.', 'Bug 1271794 doesn\'t have a uplift request date.'])
            self.assertEqual(info['backout_num'], 1)
            self.assertEqual(info['blocks'], 1)
            self.assertEqual(info['depends_on'], 2)
            self.assertEqual(info['comments'], 24)
            self.assertEqual(info['patches']['154b951082e3']['changes_size'], 76)
            self.assertEqual(info['patches']['154b951082e3']['test_changes_size'], 0)
            self.assertEqual(info['patches']['154b951082e3']['modules_num'], 3)
            self.assertEqual(info['r-ed_patches'], 0)
            self.assertEqual(info['patches']['154b951082e3']['code_churn_overall'], 249)
            self.assertEqual(info['patches']['154b951082e3']['code_churn_last_3_releases'], 245)
            self.assertEqual(info['patches']['154b951082e3']['developer_familiarity_overall'], 2)
            self.assertEqual(info['patches']['154b951082e3']['developer_familiarity_last_3_releases'], 2)
            self.assertEqual(info['patches']['154b951082e3']['reviewer_familiarity_overall'], 158)
            self.assertEqual(info['patches']['154b951082e3']['reviewer_familiarity_last_3_releases'], 157)
            self.assertEqual(len(info['patches']), 1)
            self.assertEqual(info['patches']['154b951082e3']['source'], 'mercurial')
            self.assertEqual(info['patches']['154b951082e3']['url'], 'https://hg.mozilla.org/mozilla-central/rev/154b951082e3')

        # Backed out from central and relanded on central.
        # One of the reviewers email doesn't start with his nick and he isn't in CC list.
        # The author of the patch changed his email on Bugzilla.
        info = patchanalysis.bug_analysis(679352)
        self.assertEqual(info['backout_num'], 1)
        self.assertEqual(info['blocks'], 4)
        self.assertEqual(info['depends_on'], 4)
        self.assertEqual(info['comments'], 19)
        self.assertEqual(info['patches']['b9d0984bdd95']['changes_size'], 312)
        self.assertEqual(info['patches']['f5578fdc50ef']['changes_size'], 8524)
        self.assertEqual(info['patches']['b9d0984bdd95']['test_changes_size'], 0)
        self.assertEqual(info['patches']['f5578fdc50ef']['test_changes_size'], 410)
        self.assertEqual(info['patches']['b9d0984bdd95']['modules_num'], 2)
        self.assertEqual(info['patches']['f5578fdc50ef']['modules_num'], 3)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['patches']['b9d0984bdd95']['code_churn_overall'], 406)
        self.assertEqual(info['patches']['f5578fdc50ef']['code_churn_overall'], 670)
        self.assertEqual(info['patches']['b9d0984bdd95']['code_churn_last_3_releases'], 62)
        self.assertEqual(info['patches']['f5578fdc50ef']['code_churn_last_3_releases'], 121)
        self.assertEqual(info['patches']['b9d0984bdd95']['developer_familiarity_overall'], 5)
        self.assertEqual(info['patches']['f5578fdc50ef']['developer_familiarity_overall'], 5)
        self.assertEqual(info['patches']['b9d0984bdd95']['developer_familiarity_last_3_releases'], 5)
        self.assertEqual(info['patches']['f5578fdc50ef']['developer_familiarity_last_3_releases'], 5)
        self.assertEqual(info['patches']['b9d0984bdd95']['reviewer_familiarity_overall'], 48)
        self.assertEqual(info['patches']['f5578fdc50ef']['reviewer_familiarity_overall'], 9)
        self.assertEqual(info['patches']['b9d0984bdd95']['reviewer_familiarity_last_3_releases'], 1)
        self.assertEqual(info['patches']['f5578fdc50ef']['reviewer_familiarity_last_3_releases'], 2)
        self.assertEqual(len(info['patches']), 2)
        self.assertEqual(info['patches']['b9d0984bdd95']['source'], 'mercurial')
        self.assertIn(info['patches']['b9d0984bdd95']['url'], 'https://hg.mozilla.org/mozilla-central/rev/b9d0984bdd95')
        self.assertEqual(info['patches']['f5578fdc50ef']['source'], 'mercurial')
        self.assertIn(info['patches']['f5578fdc50ef']['url'], 'https://hg.mozilla.org/mozilla-central/rev/f5578fdc50ef')

        # Changeset with multiple unrelated backouts (on fx-team).
        # Landing comment with long revision (Entire hash instead of first 12 characters).
        info = patchanalysis.bug_analysis(384458)
        self.assertEqual(info['backout_num'], 1)
        self.assertEqual(info['blocks'], 6)
        self.assertEqual(info['depends_on'], 60)
        self.assertEqual(info['comments'], 109)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['patches'], {'1c86ba5d7a5b': {'modules_num': 3, 'code_churn_overall': 406, 'changes_size': 35, 'source': 'mercurial', 'developer_familiarity_last_3_releases': 8, 'developer_familiarity_overall': 13, 'url': 'https://hg.mozilla.org/mozilla-central/rev/1c86ba5d7a5b', 'reviewer_familiarity_last_3_releases': 0, 'test_changes_size': 462, 'code_churn_last_3_releases': 57, 'reviewer_familiarity_overall': 0}, 'b94fedbf48b1': {'modules_num': 1, 'code_churn_overall': 353, 'changes_size': 1060, 'source': 'mercurial', 'developer_familiarity_last_3_releases': 10, 'developer_familiarity_overall': 41, 'url': 'https://hg.mozilla.org/mozilla-central/rev/b94fedbf48b1', 'reviewer_familiarity_last_3_releases': 0, 'test_changes_size': 0, 'code_churn_last_3_releases': 34, 'reviewer_familiarity_overall': 0}, '0d05e6a1bdc2': {'modules_num': 1, 'code_churn_overall': 25, 'changes_size': 72, 'source': 'mercurial', 'developer_familiarity_last_3_releases': 2, 'developer_familiarity_overall': 2, 'url': 'https://hg.mozilla.org/mozilla-central/rev/0d05e6a1bdc2', 'reviewer_familiarity_last_3_releases': 0, 'test_changes_size': 0, 'code_churn_last_3_releases': 5, 'reviewer_familiarity_overall': 0}, 'de5d300e4687': {'modules_num': 3, 'code_churn_overall': 3805, 'changes_size': 358, 'source': 'mercurial', 'developer_familiarity_last_3_releases': 11, 'developer_familiarity_overall': 43, 'url': 'https://hg.mozilla.org/mozilla-central/rev/de5d300e4687', 'reviewer_familiarity_last_3_releases': 0, 'test_changes_size': 0, 'code_churn_last_3_releases': 363, 'reviewer_familiarity_overall': 1}, '73176395400e': {'modules_num': 3, 'code_churn_overall': 3616, 'changes_size': 1227, 'source': 'mercurial', 'developer_familiarity_last_3_releases': 20, 'developer_familiarity_overall': 63, 'url': 'https://hg.mozilla.org/mozilla-central/rev/73176395400e', 'reviewer_familiarity_last_3_releases': 0, 'test_changes_size': 0, 'code_churn_last_3_releases': 354, 'reviewer_familiarity_overall': 1}})

        # Custom backout (no reference to revision).
        # Author has a different name on Bugzilla and Mercurial and they don't use the email on Mercurial.
        with warnings.catch_warnings(record=True) as w:
            info = patchanalysis.bug_analysis(1220307)
            if sys.version_info >= (3, 0):
                self.assertWarnings(w, ['da10eecd0e76 looks like a backout, but we couldn\'t find which revision was backed out.', 'Revision da10eecd0e76 is related to another bug (1276850).', 'Bug 1220307 doesn\'t have a uplift request date.'])
            self.assertEqual(info['backout_num'], 2)
            self.assertEqual(info['blocks'], 4)
            self.assertEqual(info['depends_on'], 1)
            self.assertEqual(info['comments'], 42)
            self.assertEqual(info['r-ed_patches'], 0)
            self.assertEqual(info['patches'], {'6126c53203f8': {'developer_familiarity_overall': 4, 'developer_familiarity_last_3_releases': 4, 'test_changes_size': 0, 'source': 'mercurial', 'modules_num': 1, 'changes_size': 40, 'code_churn_last_3_releases': 13, 'url': 'https://hg.mozilla.org/mozilla-central/rev/6126c53203f8', 'code_churn_overall': 14, 'reviewer_familiarity_last_3_releases': 1, 'reviewer_familiarity_overall': 1}, 'c17c6b68112c': {'developer_familiarity_overall': 1, 'developer_familiarity_last_3_releases': 1, 'test_changes_size': 50, 'source': 'mercurial', 'modules_num': 1, 'changes_size': 0, 'code_churn_last_3_releases': 5, 'url': 'https://hg.mozilla.org/mozilla-central/rev/c17c6b68112c', 'code_churn_overall': 13, 'reviewer_familiarity_last_3_releases': 0, 'reviewer_familiarity_overall': 0}, '933b5260480f': {'developer_familiarity_overall': 0, 'developer_familiarity_last_3_releases': 0, 'test_changes_size': 0, 'source': 'mercurial', 'modules_num': 1, 'changes_size': 27, 'code_churn_last_3_releases': 15, 'url': 'https://hg.mozilla.org/mozilla-central/rev/933b5260480f', 'code_churn_overall': 52, 'reviewer_familiarity_last_3_releases': 0, 'reviewer_familiarity_overall': 1}})

        with warnings.catch_warnings(record=True) as w:
            info = patchanalysis.bug_analysis(1276850)
            if sys.version_info >= (3, 0):
                self.assertWarnings(w, ['da10eecd0e76 looks like a backout, but we couldn\'t find which revision was backed out.', 'Author bugmail@mozilla.staktrace.com is not in the list of authors on Bugzilla.', 'Bug 1276850 doesn\'t have a uplift request date.'])
            self.assertEqual(info['backout_num'], 0)
            self.assertEqual(info['blocks'], 1)
            self.assertEqual(info['depends_on'], 0)
            self.assertEqual(info['comments'], 24)
            self.assertEqual(info['r-ed_patches'], 0)
            self.assertEqual(info['patches'], {'da10eecd0e76': {'source': 'mercurial', 'developer_familiarity_overall': 0, 'code_churn_overall': 26, 'test_changes_size': 0, 'developer_familiarity_last_3_releases': 0, 'code_churn_last_3_releases': 21, 'url': 'https://hg.mozilla.org/mozilla-central/rev/da10eecd0e76', 'modules_num': 1, 'reviewer_familiarity_last_3_releases': 21, 'changes_size': 40, 'reviewer_familiarity_overall': 26}})

        # No landed patches.
        # The author of the patch changed his email on Bugzilla, so past contributions
        # are hard to find.
        info = patchanalysis.bug_analysis(1007402)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 1)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 41)
        self.assertEqual(info['r-ed_patches'], 1)
        self.assertEqual(info['patches'], {8447556: {'test_changes_size': 445, 'code_churn_last_3_releases': 316, 'reviewer_familiarity_overall': 266, 'developer_familiarity_overall': 4, 'modules_num': 6, 'developer_familiarity_last_3_releases': 4, 'code_churn_overall': 2465, 'source': 'attachment', 'url': 'https://bugzilla.mozilla.org/attachment.cgi?id=8447556', 'reviewer_familiarity_last_3_releases': 15, 'changes_size': 1020}, 8447557: {'test_changes_size': 0, 'code_churn_last_3_releases': 0, 'reviewer_familiarity_overall': 0, 'developer_familiarity_overall': 0, 'modules_num': 0, 'developer_familiarity_last_3_releases': 0, 'code_churn_overall': 0, 'source': 'attachment', 'url': 'https://bugzilla.mozilla.org/attachment.cgi?id=8447557', 'reviewer_familiarity_last_3_releases': 0, 'changes_size': 15}})

        # No link between Bugzilla account and Mercurial author.
        # Reviewer uses different email on Bugzilla and Mercurial.
        info = patchanalysis.bug_analysis(901821)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 1)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 11)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['patches'], {'b43afcd4e347': {'developer_familiarity_last_3_releases': 23, 'developer_familiarity_overall': 115, 'code_churn_overall': 1088, 'source': 'mercurial', 'reviewer_familiarity_overall': 0, 'url': 'https://hg.mozilla.org/mozilla-central/rev/b43afcd4e347', 'changes_size': 18, 'test_changes_size': 0, 'reviewer_familiarity_last_3_releases': 0, 'code_churn_last_3_releases': 152, 'modules_num': 1}})

        # Reviewer has different emails on Bugzilla and Mercurial, and his short name is hard to find.
        info = patchanalysis.bug_analysis(859425)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 0)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 8)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['patches'], {'5549afae23a7': {'test_changes_size': 0, 'modules_num': 1, 'source': 'mercurial', 'reviewer_familiarity_last_3_releases': 0, 'developer_familiarity_overall': 1, 'code_churn_last_3_releases': 30, 'changes_size': 31, 'reviewer_familiarity_overall': 0, 'code_churn_overall': 79, 'url': 'https://hg.mozilla.org/mozilla-central/rev/5549afae23a7', 'developer_familiarity_last_3_releases': 1}})

        # r=bustage
        info = patchanalysis.bug_analysis(701875)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 3)
        self.assertEqual(info['depends_on'], 1)
        self.assertEqual(info['comments'], 69)
        self.assertEqual(info['r-ed_patches'], 1)
        self.assertEqual(info['patches'], {'3f0b94325b80': {'modules_num': 4, 'code_churn_last_3_releases': 330, 'url': 'https://hg.mozilla.org/mozilla-central/rev/3f0b94325b80', 'code_churn_overall': 2312, 'source': 'mercurial', 'reviewer_familiarity_last_3_releases': 0, 'changes_size': 165, 'reviewer_familiarity_overall': 0, 'developer_familiarity_last_3_releases': 7, 'test_changes_size': 0, 'developer_familiarity_overall': 61}, '7ae3089be8a5': {'modules_num': 1, 'code_churn_last_3_releases': 196, 'url': 'https://hg.mozilla.org/mozilla-central/rev/7ae3089be8a5', 'code_churn_overall': 1458, 'source': 'mercurial', 'reviewer_familiarity_last_3_releases': 196, 'changes_size': 29, 'reviewer_familiarity_overall': 1458, 'developer_familiarity_last_3_releases': 5, 'test_changes_size': 0, 'developer_familiarity_overall': 25}})

        # Reviewer doesn't have his short name in his Bugzilla name.
        with warnings.catch_warnings(record=True) as w:
            info = patchanalysis.bug_analysis(853033)
            self.assertWarnings(w, ['Revision 8de609c5d378 is related to another bug (743252).', 'Reviewer jlebar could not be found.'])
            self.assertEqual(info['backout_num'], 0)
            self.assertEqual(info['blocks'], 2)
            self.assertEqual(info['depends_on'], 0)
            self.assertEqual(info['comments'], 13)
            self.assertEqual(info['r-ed_patches'], 0)
            self.assertEqual(info['patches'], {'bb210464e583': {'reviewer_familiarity_last_3_releases': 0, 'developer_familiarity_overall': 1, 'source': 'mercurial', 'modules_num': 1, 'code_churn_last_3_releases': 1, 'developer_familiarity_last_3_releases': 1, 'reviewer_familiarity_overall': 0, 'code_churn_overall': 4, 'test_changes_size': 0, 'changes_size': 18, 'url': 'https://hg.mozilla.org/mozilla-central/rev/bb210464e583'}})

        # There are users in the CC list with empty real names.
        info = patchanalysis.bug_analysis(699633)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 0)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 41)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['patches'], {'936643625d71': {'code_churn_last_3_releases': 66, 'modules_num': 1, 'code_churn_overall': 66, 'reviewer_familiarity_last_3_releases': 0, 'source': 'mercurial', 'url': 'https://hg.mozilla.org/mozilla-central/rev/936643625d71', 'developer_familiarity_overall': 28, 'test_changes_size': 35, 'developer_familiarity_last_3_releases': 28, 'changes_size': 177, 'reviewer_familiarity_overall': 0}})

        # Reviewer with several IRC names.
        info = patchanalysis.bug_analysis(914034)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 2)
        self.assertEqual(info['depends_on'], 1)
        self.assertEqual(info['comments'], 26)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['patches'], {'a13edd3c49e7': {'source': 'mercurial', 'developer_familiarity_overall': 7, 'test_changes_size': 0, 'modules_num': 1, 'code_churn_last_3_releases': 27, 'developer_familiarity_last_3_releases': 7, 'reviewer_familiarity_last_3_releases': 2, 'changes_size': 287, 'reviewer_familiarity_overall': 3, 'code_churn_overall': 240, 'url': 'https://hg.mozilla.org/mozilla-central/rev/a13edd3c49e7'}})

        # IRC handle in the domain of the email (mozilla@IRCHANDLE.org).
        info = patchanalysis.bug_analysis(903475)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 1)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 71)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['patches'], {'d76cd808a5fc': {'source': 'mercurial', 'modules_num': 1, 'developer_familiarity_last_3_releases': 0, 'changes_size': 18, 'code_churn_overall': 13, 'reviewer_familiarity_last_3_releases': 0, 'reviewer_familiarity_overall': 0, 'test_changes_size': 0, 'developer_familiarity_overall': 0, 'url': 'https://hg.mozilla.org/mozilla-central/rev/d76cd808a5fc', 'code_churn_last_3_releases': 3}})

        # Backout without the 'changeset' word.
        info = patchanalysis.bug_analysis(829421)
        self.assertEqual(info['backout_num'], 1)
        self.assertEqual(info['blocks'], 0)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 22)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['patches'], {'9f56d7e548f1': {'reviewer_familiarity_overall': 11, 'test_changes_size': 0, 'reviewer_familiarity_last_3_releases': 4, 'developer_familiarity_last_3_releases': 0, 'url': 'https://hg.mozilla.org/mozilla-central/rev/9f56d7e548f1', 'developer_familiarity_overall': 0, 'modules_num': 1, 'source': 'mercurial', 'code_churn_overall': 110, 'changes_size': 21, 'code_churn_last_3_releases': 21}})

        # IRC handle first character is lower case in Mercurial, upper case in Bugzilla.
        info = patchanalysis.bug_analysis(799266)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 0)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 28)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['patches'], {'53ae9eb476e9': {'reviewer_familiarity_overall': 1, 'url': 'https://hg.mozilla.org/mozilla-central/rev/53ae9eb476e9', 'developer_familiarity_last_3_releases': 5, 'code_churn_overall': 355, 'developer_familiarity_overall': 36, 'test_changes_size': 0, 'modules_num': 1, 'changes_size': 104, 'reviewer_familiarity_last_3_releases': 0, 'source': 'mercurial', 'code_churn_last_3_releases': 37}})

        # r=IRC_HANDLE_OF_THE_AUTHOR
        info = patchanalysis.bug_analysis(721760)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 0)
        self.assertEqual(info['depends_on'], 1)
        self.assertEqual(info['comments'], 72)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['patches'], {'2ef72ec44da3': {'code_churn_last_3_releases': 1, 'modules_num': 1, 'source': 'mercurial', 'code_churn_overall': 2, 'test_changes_size': 0, 'url': 'https://hg.mozilla.org/mozilla-central/rev/2ef72ec44da3', 'developer_familiarity_last_3_releases': 0, 'changes_size': 44, 'reviewer_familiarity_last_3_releases': 0, 'reviewer_familiarity_overall': 0, 'developer_familiarity_overall': 0}, '66b36a145f89': {'code_churn_last_3_releases': 24, 'modules_num': 1, 'source': 'mercurial', 'code_churn_overall': 36, 'test_changes_size': 0, 'url': 'https://hg.mozilla.org/mozilla-central/rev/66b36a145f89', 'developer_familiarity_last_3_releases': 17, 'changes_size': 172, 'reviewer_familiarity_last_3_releases': 6, 'reviewer_familiarity_overall': 13, 'developer_familiarity_overall': 28}})

        # IRC handle is ':IRC_HANDLE.SURNAME' and reviewer is not a reviewer of the patch on Bugzilla.
        info = patchanalysis.bug_analysis(1021265)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 3)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 111)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['patches'], {'3d0169c5795f': {'changes_size': 92, 'test_changes_size': 0, 'developer_familiarity_overall': 23, 'reviewer_familiarity_overall': 16, 'modules_num': 2, 'code_churn_last_3_releases': 62, 'source': 'mercurial', 'url': 'https://hg.mozilla.org/mozilla-central/rev/3d0169c5795f', 'reviewer_familiarity_last_3_releases': 6, 'code_churn_overall': 863, 'developer_familiarity_last_3_releases': 5}, '1b07e2892e9d': {'changes_size': 45, 'test_changes_size': 0, 'developer_familiarity_overall': 16, 'reviewer_familiarity_overall': 11, 'modules_num': 1, 'code_churn_last_3_releases': 28, 'source': 'mercurial', 'url': 'https://hg.mozilla.org/mozilla-central/rev/1b07e2892e9d', 'reviewer_familiarity_last_3_releases': 2, 'code_churn_overall': 299, 'developer_familiarity_last_3_releases': 5}, '0b298d91fbdd': {'changes_size': 18, 'test_changes_size': 0, 'developer_familiarity_overall': 15, 'reviewer_familiarity_overall': 298, 'modules_num': 1, 'code_churn_last_3_releases': 28, 'source': 'mercurial', 'url': 'https://hg.mozilla.org/mozilla-central/rev/0b298d91fbdd', 'reviewer_familiarity_last_3_releases': 28, 'code_churn_overall': 298, 'developer_familiarity_last_3_releases': 4}, '96f0df721845': {'changes_size': 18, 'test_changes_size': 0, 'developer_familiarity_overall': 12, 'reviewer_familiarity_overall': 0, 'modules_num': 1, 'code_churn_last_3_releases': 32, 'source': 'mercurial', 'url': 'https://hg.mozilla.org/mozilla-central/rev/96f0df721845', 'reviewer_familiarity_last_3_releases': 0, 'code_churn_overall': 303, 'developer_familiarity_last_3_releases': 3}})

        # IRC handle is the beginning of the real name with a space after.
        info = patchanalysis.bug_analysis(1029098)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 1)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 15)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['patches'], {'d41a6d09ccd6': {'test_changes_size': 97, 'code_churn_last_3_releases': 15, 'url': 'https://hg.mozilla.org/mozilla-central/rev/d41a6d09ccd6', 'code_churn_overall': 277, 'reviewer_familiarity_overall': 9, 'modules_num': 1, 'reviewer_familiarity_last_3_releases': 0, 'developer_familiarity_last_3_releases': 8, 'changes_size': 94, 'source': 'mercurial', 'developer_familiarity_overall': 81}})

        # Typo in the reviewer name.
        with warnings.catch_warnings(record=True) as w:
            info = patchanalysis.bug_analysis(843733)
            self.assertWarnings(w, ['Reviewer mjronseb could not be found.'])

        # r=oops
        info = patchanalysis.bug_analysis(843821)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 1)
        self.assertEqual(info['depends_on'], 1)
        self.assertEqual(info['comments'], 21)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['patches'], {'b2c38a3b59dc': {'code_churn_overall': 8, 'changes_size': 19, 'modules_num': 1, 'reviewer_familiarity_overall': 8, 'source': 'mercurial', 'developer_familiarity_last_3_releases': 7, 'developer_familiarity_overall': 7, 'url': 'https://hg.mozilla.org/mozilla-central/rev/b2c38a3b59dc', 'reviewer_familiarity_last_3_releases': 8, 'code_churn_last_3_releases': 8, 'test_changes_size': 0}, '3c11909c216a': {'code_churn_overall': 879, 'changes_size': 129, 'modules_num': 1, 'reviewer_familiarity_overall': 0, 'source': 'mercurial', 'developer_familiarity_last_3_releases': 12, 'developer_familiarity_overall': 124, 'url': 'https://hg.mozilla.org/mozilla-central/rev/3c11909c216a', 'reviewer_familiarity_last_3_releases': 0, 'code_churn_last_3_releases': 141, 'test_changes_size': 0}})

        # r=backout
        info = patchanalysis.bug_analysis(679509)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 0)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 97)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['patches'], {'8c59e49aea63': {'developer_familiarity_overall': 0, 'developer_familiarity_last_3_releases': 0, 'url': 'https://hg.mozilla.org/mozilla-central/rev/8c59e49aea63', 'modules_num': 1, 'changes_size': 17, 'reviewer_familiarity_last_3_releases': 0, 'code_churn_last_3_releases': 9, 'test_changes_size': 36, 'reviewer_familiarity_overall': 0, 'code_churn_overall': 11, 'source': 'mercurial'}, '38f53f45bbf4': {'developer_familiarity_overall': 113, 'developer_familiarity_last_3_releases': 40, 'url': 'https://hg.mozilla.org/mozilla-central/rev/38f53f45bbf4', 'modules_num': 2, 'changes_size': 145, 'reviewer_familiarity_last_3_releases': 41, 'code_churn_last_3_releases': 294, 'test_changes_size': 36, 'reviewer_familiarity_overall': 50, 'code_churn_overall': 1811, 'source': 'mercurial'}, '97f2fc986824': {'developer_familiarity_overall': 0, 'developer_familiarity_last_3_releases': 0, 'url': 'https://hg.mozilla.org/mozilla-central/rev/97f2fc986824', 'modules_num': 1, 'changes_size': 84, 'reviewer_familiarity_last_3_releases': 0, 'code_churn_last_3_releases': 9, 'test_changes_size': 0, 'reviewer_familiarity_overall': 0, 'code_churn_overall': 18, 'source': 'mercurial'}, '40f077f9c4a2': {'developer_familiarity_overall': 3, 'developer_familiarity_last_3_releases': 3, 'url': 'https://hg.mozilla.org/mozilla-central/rev/40f077f9c4a2', 'modules_num': 1, 'changes_size': 101, 'reviewer_familiarity_last_3_releases': 22, 'code_churn_last_3_releases': 22, 'test_changes_size': 36, 'reviewer_familiarity_overall': 34, 'code_churn_overall': 34, 'source': 'mercurial'}})

        # Bugzilla user is impossible to find from IRC handle.
        with warnings.catch_warnings(record=True) as w:
            info = patchanalysis.bug_analysis(700583)
            self.assertWarnings(w, ['Reviewer jocheng@mozilla.com is not in the list of reviewers on Bugzilla.', 'Bug 700583 doesn\'t have a uplift request date.'])

        # IRC handle is name+surname
        info = patchanalysis.bug_analysis(701262)

        # r=none
        info = patchanalysis.bug_analysis(733614)

        # Reviewer on Bugzilla is a different person than the reviewer in the Mercurial commit.
        with warnings.catch_warnings(record=True) as w:
            info = patchanalysis.bug_analysis(963621)
            self.assertWarnings(w, ['Reviewer doublec could not be found.'])

        # IRC handle is part of the name.
        info = patchanalysis.bug_analysis(829646)

        # Multiple backouts with a commit message of one line.
        info = patchanalysis.bug_analysis(683280)

        # IRC handle on Bugzilla is different than the one used in Mercurial.
        info = patchanalysis.bug_analysis(680802)

        # Weird situation: the mozilla-central commit referenced in the comments is from some other
        # bug and the actual patch from the bug never landed on mozilla-central but directly on
        # other channels.
        try:
            info = patchanalysis.bug_analysis(846986)
        except Exception as e:
            self.assertTrue(str(e) in ['Too many matching authors (jwalden+bmo@mit.edu, anarchy@gentoo.org) found for jwalden@mit.edu', 'Too many matching authors (anarchy@gentoo.org, jwalden+bmo@mit.edu) found for jwalden@mit.edu'])

        # A comment contains a non-existing revision.
        with warnings.catch_warnings(record=True) as w:
            info = patchanalysis.bug_analysis(1156913)
            self.assertWarnings(w, ['Revision fa8854bd0029 doesn\'t exist.'])

        # Author in mercurial doesn't use the same format as usual ("Full Name email" instead of "Full Name <email>").
        info = patchanalysis.bug_analysis(1277522)

        # Author in mercurial doesn't have email
        info = patchanalysis.bug_analysis(1254980)

        # Check uplift request
        info = patchanalysis.bug_analysis(1230065)

        self.assertIsNotNone(info['uplift_comment'])
        self.assertEqual(len(info['uplift_comment']['text'].split('\n')), 11)
        self.assertEqual(info['uplift_comment']['id'], 11222288)
        self.assertIsNotNone(info['uplift_author'])
        self.assertEqual(info['uplift_author']['email'], 'karlt@mozbugz.karlt.net')

        # in-testsuite?
        info = patchanalysis.bug_analysis(1190)
        self.assertEqual(info['in-testsuite'], '?')
        # in-testsuite-
        info = patchanalysis.bug_analysis(91)
        self.assertEqual(info['in-testsuite'], '-')
        # in-testsuite+
        info = patchanalysis.bug_analysis(105)
        self.assertEqual(info['in-testsuite'], '+')
        # in-testsuite not set
        info = patchanalysis.bug_analysis(1234567)
        self.assertEqual(info['in-testsuite'], '')

    @responses.activate
    def test_uplift_info(self):
        info = patchanalysis.uplift_info(909494, 'release')
        self.assertEqual(info['landing_delta'], timedelta(0, 1091))
        self.assertEqual(info['release_delta'], timedelta(17, 44927))
        self.assertEqual(info['uplift_accepted'], False)
        self.assertEqual(info['response_delta'], timedelta(0, 843))
        self.assertEqual(info['uplift_author']['email'], 'sunfish@mozilla.com')
        self.assertEqual(info['uplift_comment']['id'], 7810070)
        self.assertEqual(len(info['uplift_comment']['text'].split('\n')), 14)

        # Approved without request.
        with warnings.catch_warnings(record=True) as w:
            info = patchanalysis.uplift_info(859425, 'release')
            self.assertWarnings(w, ['Bug 859425 doesn\'t have a uplift request date.'])
            self.assertEqual(info['landing_delta'], timedelta(1, 60500))
            self.assertEqual(info['release_delta'], timedelta(33, 50345))
            self.assertEqual(info['uplift_accepted'], True)
            self.assertEqual(info['response_delta'], timedelta(0))
            self.assertEqual(info['uplift_author']['email'], 'mark.finkle@gmail.com')
            self.assertEqual(info['uplift_comment']['id'], 7292379)
            self.assertEqual(len(info['uplift_comment']['text'].split('\n')), 9)

        # Pending request.
        with warnings.catch_warnings(record=True) as w:
            info = patchanalysis.uplift_info(1283017, 'aurora')
            self.assertEqual(info['landing_delta'], timedelta(-14, 66356))
            self.assertEqual(info['release_delta'], timedelta(32, 12341))
            self.assertEqual(info['uplift_accepted'], True)
            self.assertEqual(info['uplift_author']['email'], 'cyu@mozilla.com')
            self.assertEqual(info['uplift_comment']['id'], 11516158)
            self.assertEqual(len(info['uplift_comment']['text'].split('\n')), 9)

        # Multiple requests in the same bug, one accepted, one rejected.
        try:
            info = patchanalysis.uplift_info(1229760, 'release')
        except Exception as e:
            self.assertEqual(str(e), 'Uplift either accepted or rejected.')

    @responses.activate
    def test_patch_info(self):
        info = patchanalysis.get_patch_info(['668639'])
        self.assertEqual(list(info.keys()), ['668639'])
        info = info['668639']
        self.assertEqual(info['affected'], set())
        self.assertEqual(info['approval'], {'aurora', 'beta', 'release'})
        self.assertEqual(info['land']['aurora'], utils.get_date_ymd('2011-07-07 19:58:31'))
        self.assertEqual(info['land']['beta'], utils.get_date_ymd('2011-07-07 19:59:52'))
        self.assertEqual(info['land']['release'], utils.get_date_ymd('2011-07-07 23:25:27'))
        self.assertEqual(info['land']['nightly'], utils.get_date_ymd('2011-07-07 19:25:02'))


if __name__ == '__main__':
    unittest.main()
