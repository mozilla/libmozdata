# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
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

    @responses.activate
    def test_bug_analysis(self):
        info = patchanalysis.bug_analysis(547914)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 1)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 11)
        self.assertEqual(info['changes_size'], 640)
        self.assertEqual(info['test_changes_size'], 0)
        self.assertEqual(info['modules_num'], 1)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 205)
        self.assertEqual(info['code_churn_last_3_releases'], 36)
        self.assertEqual(info['developer_familiarity_overall'], 13)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 1)
        self.assertEqual(info['reviewer_familiarity_overall'], 0)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 0)
        self.assertIn('shaver@mozilla.org', info['users']['reviewers'])
        self.assertIn('gerv@mozilla.org', info['users']['reviewers'])
        self.assertEqual(info['users']['assignee']['email'], 'philringnalda@gmail.com')

        self.assertGreater(info['crashes'], 0)

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
        self.assertEqual(info['changes_size'], 488)
        self.assertEqual(info['test_changes_size'], 0)
        self.assertEqual(info['modules_num'], 3)
        self.assertEqual(info['r-ed_patches'], 3)
        self.assertEqual(info['code_churn_overall'], 184)
        self.assertEqual(info['code_churn_last_3_releases'], 31)
        self.assertEqual(info['developer_familiarity_overall'], 4)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 4)
        self.assertEqual(info['reviewer_familiarity_overall'], 16)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 0)
        self.assertGreater(info['crashes'], 0)

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
            self.assertEqual(info['changes_size'], 76)
            self.assertEqual(info['test_changes_size'], 0)
            self.assertEqual(info['modules_num'], 3)
            self.assertEqual(info['r-ed_patches'], 0)
            self.assertEqual(info['code_churn_overall'], 249)
            self.assertEqual(info['code_churn_last_3_releases'], 245)
            self.assertEqual(info['developer_familiarity_overall'], 2)
            self.assertEqual(info['developer_familiarity_last_3_releases'], 2)
            self.assertEqual(info['reviewer_familiarity_overall'], 158)
            self.assertEqual(info['reviewer_familiarity_last_3_releases'], 157)
            self.assertGreaterEqual(info['crashes'], 0)

        # Backed out from central and relanded on central.
        # One of the reviewers email doesn't start with his nick and he isn't in CC list.
        # The author of the patch changed his email on Bugzilla.
        info = patchanalysis.bug_analysis(679352)
        self.assertEqual(info['backout_num'], 1)
        self.assertEqual(info['blocks'], 4)
        self.assertEqual(info['depends_on'], 4)
        self.assertEqual(info['comments'], 19)
        self.assertEqual(info['changes_size'], 8836)
        self.assertEqual(info['test_changes_size'], 410)
        self.assertEqual(info['modules_num'], 5)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 1076)
        self.assertEqual(info['code_churn_last_3_releases'], 183)
        self.assertEqual(info['developer_familiarity_overall'], 10)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 10)
        self.assertEqual(info['reviewer_familiarity_overall'], 57)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 3)
        self.assertGreater(info['crashes'], 0)

        # Changeset with multiple unrelated backouts (on fx-team).
        # Landing comment with long revision (Entire hash instead of first 12 characters).
        info = patchanalysis.bug_analysis(384458)
        self.assertEqual(info['backout_num'], 1)
        self.assertEqual(info['blocks'], 6)
        self.assertEqual(info['depends_on'], 47)
        self.assertEqual(info['comments'], 106)
        self.assertEqual(info['changes_size'], 2752)
        self.assertEqual(info['test_changes_size'], 462)
        self.assertEqual(info['modules_num'], 11)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 8191)
        self.assertEqual(info['code_churn_last_3_releases'], 801)
        self.assertEqual(info['developer_familiarity_overall'], 162)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 51)
        self.assertEqual(info['reviewer_familiarity_overall'], 2)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 0)
        self.assertGreater(info['crashes'], 0)

        # Custom backout (no reference to revision).
        # Author has a different name on Bugzilla and Mercurial and they don't use the email on Mercurial.
        with warnings.catch_warnings(record=True) as w:
            info = patchanalysis.bug_analysis(1220307)
            self.assertWarnings(w, ['da10eecd0e76 looks like a backout, but we couldn\'t find which revision was backed out.', 'Revision da10eecd0e76 is related to another bug (1276850).', 'Bug 1220307 doesn\'t have a uplift request date.'])
            self.assertEqual(info['backout_num'], 2)
            self.assertEqual(info['blocks'], 4)
            self.assertEqual(info['depends_on'], 1)
            self.assertEqual(info['comments'], 42)
            self.assertEqual(info['changes_size'], 67)
            self.assertEqual(info['test_changes_size'], 50)
            self.assertEqual(info['modules_num'], 3)
            self.assertEqual(info['r-ed_patches'], 0)
            self.assertEqual(info['code_churn_overall'], 79)
            self.assertEqual(info['code_churn_last_3_releases'], 33)
            self.assertEqual(info['developer_familiarity_overall'], 5)
            self.assertEqual(info['developer_familiarity_last_3_releases'], 5)
            self.assertEqual(info['reviewer_familiarity_overall'], 2)
            self.assertEqual(info['reviewer_familiarity_last_3_releases'], 1)
            self.assertGreater(info['crashes'], 0)

        with warnings.catch_warnings(record=True) as w:
            info = patchanalysis.bug_analysis(1276850)
            self.assertWarnings(w, ['da10eecd0e76 looks like a backout, but we couldn\'t find which revision was backed out.', 'Author bugmail@mozilla.staktrace.com is not in the list of authors on Bugzilla.', 'Bug 1276850 doesn\'t have a uplift request date.'])
            self.assertEqual(info['backout_num'], 0)
            self.assertEqual(info['blocks'], 1)
            self.assertEqual(info['depends_on'], 0)
            self.assertEqual(info['comments'], 24)
            self.assertEqual(info['changes_size'], 40)
            self.assertEqual(info['test_changes_size'], 0)
            self.assertEqual(info['modules_num'], 1)
            self.assertEqual(info['r-ed_patches'], 0)
            self.assertEqual(info['code_churn_overall'], 26)
            self.assertEqual(info['code_churn_last_3_releases'], 21)
            self.assertEqual(info['developer_familiarity_overall'], 0)
            self.assertEqual(info['developer_familiarity_last_3_releases'], 0)
            self.assertEqual(info['reviewer_familiarity_overall'], 26)
            self.assertEqual(info['reviewer_familiarity_last_3_releases'], 21)
            self.assertGreater(info['crashes'], 0)

        # No landed patches.
        # The author of the patch changed his email on Bugzilla, so past contributions
        # are hard to find.
        info = patchanalysis.bug_analysis(1007402)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 1)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 41)
        self.assertEqual(info['changes_size'], 1035)
        self.assertEqual(info['test_changes_size'], 445)
        self.assertEqual(info['modules_num'], 6)
        self.assertEqual(info['r-ed_patches'], 1)
        self.assertEqual(info['code_churn_overall'], 2465)
        self.assertEqual(info['code_churn_last_3_releases'], 316)
        self.assertEqual(info['developer_familiarity_overall'], 4)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 4)
        self.assertEqual(info['reviewer_familiarity_overall'], 266)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 15)
        self.assertGreaterEqual(info['crashes'], 0)

        # No link between Bugzilla account and Mercurial author.
        # Reviewer uses different email on Bugzilla and Mercurial.
        info = patchanalysis.bug_analysis(901821)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 1)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 11)
        self.assertEqual(info['changes_size'], 18)
        self.assertEqual(info['test_changes_size'], 0)
        self.assertEqual(info['modules_num'], 1)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 1088)
        self.assertEqual(info['code_churn_last_3_releases'], 152)
        self.assertEqual(info['developer_familiarity_overall'], 115)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 23)
        self.assertEqual(info['reviewer_familiarity_overall'], 0)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 0)
        self.assertGreaterEqual(info['crashes'], 0)

        # Reviewer has different emails on Bugzilla and Mercurial, and his short name is hard to find.
        info = patchanalysis.bug_analysis(859425)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 0)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 8)
        self.assertEqual(info['changes_size'], 31)
        self.assertEqual(info['test_changes_size'], 0)
        self.assertEqual(info['modules_num'], 1)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 79)
        self.assertEqual(info['code_churn_last_3_releases'], 30)
        self.assertEqual(info['developer_familiarity_overall'], 1)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 1)
        self.assertEqual(info['reviewer_familiarity_overall'], 0)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 0)
        self.assertGreaterEqual(info['crashes'], 0)

        # r=bustage
        info = patchanalysis.bug_analysis(701875)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 3)
        self.assertEqual(info['depends_on'], 1)
        self.assertEqual(info['comments'], 69)
        self.assertEqual(info['changes_size'], 194)
        self.assertEqual(info['test_changes_size'], 0)
        self.assertEqual(info['modules_num'], 5)
        self.assertEqual(info['r-ed_patches'], 1)
        self.assertEqual(info['code_churn_overall'], 3770)
        self.assertEqual(info['code_churn_last_3_releases'], 526)
        self.assertEqual(info['developer_familiarity_overall'], 86)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 12)
        self.assertEqual(info['reviewer_familiarity_overall'], 25)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 5)
        self.assertGreaterEqual(info['crashes'], 0)

        # Reviewer doesn't have his short name in his Bugzilla name.
        with warnings.catch_warnings(record=True) as w:
            info = patchanalysis.bug_analysis(853033)
            self.assertWarnings(w, ['Revision 8de609c5d378 is related to another bug (743252).', 'Reviewer jlebar could not be found.'])
            self.assertEqual(info['backout_num'], 0)
            self.assertEqual(info['blocks'], 2)
            self.assertEqual(info['depends_on'], 0)
            self.assertEqual(info['comments'], 13)
            self.assertEqual(info['changes_size'], 18)
            self.assertEqual(info['test_changes_size'], 0)
            self.assertEqual(info['modules_num'], 1)
            self.assertEqual(info['r-ed_patches'], 0)
            self.assertEqual(info['code_churn_overall'], 4)
            self.assertEqual(info['code_churn_last_3_releases'], 1)
            self.assertEqual(info['developer_familiarity_overall'], 1)
            self.assertEqual(info['developer_familiarity_last_3_releases'], 1)
            self.assertEqual(info['reviewer_familiarity_overall'], 0)
            self.assertEqual(info['reviewer_familiarity_last_3_releases'], 0)
            self.assertGreaterEqual(info['crashes'], 0)

        # There are users in the CC list with empty real names.
        info = patchanalysis.bug_analysis(699633)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 0)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 41)
        self.assertEqual(info['changes_size'], 179)
        self.assertEqual(info['test_changes_size'], 35)
        self.assertEqual(info['modules_num'], 1)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 66)
        self.assertEqual(info['code_churn_last_3_releases'], 66)
        self.assertEqual(info['developer_familiarity_overall'], 28)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 28)
        self.assertEqual(info['reviewer_familiarity_overall'], 0)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 0)
        self.assertGreaterEqual(info['crashes'], 0)

        # Reviewer with several IRC names.
        info = patchanalysis.bug_analysis(914034)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 2)
        self.assertEqual(info['depends_on'], 1)
        self.assertEqual(info['comments'], 26)
        self.assertEqual(info['changes_size'], 287)
        self.assertEqual(info['test_changes_size'], 0)
        self.assertEqual(info['modules_num'], 1)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 240)
        self.assertEqual(info['code_churn_last_3_releases'], 27)
        self.assertEqual(info['developer_familiarity_overall'], 7)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 7)
        self.assertEqual(info['reviewer_familiarity_overall'], 3)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 2)
        self.assertGreaterEqual(info['crashes'], 0)

        # IRC handle in the domain of the email (mozilla@IRCHANDLE.org).
        info = patchanalysis.bug_analysis(903475)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 1)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 71)
        self.assertEqual(info['changes_size'], 18)
        self.assertEqual(info['test_changes_size'], 0)
        self.assertEqual(info['modules_num'], 1)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 13)
        self.assertEqual(info['code_churn_last_3_releases'], 3)
        self.assertEqual(info['developer_familiarity_overall'], 0)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 0)
        self.assertEqual(info['reviewer_familiarity_overall'], 0)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 0)
        self.assertGreaterEqual(info['crashes'], 0)

        # Backout without the 'changeset' word.
        info = patchanalysis.bug_analysis(829421)
        self.assertEqual(info['backout_num'], 1)
        self.assertEqual(info['blocks'], 0)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 22)
        self.assertEqual(info['changes_size'], 21)
        self.assertEqual(info['test_changes_size'], 0)
        self.assertEqual(info['modules_num'], 1)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 110)
        self.assertEqual(info['code_churn_last_3_releases'], 21)
        self.assertEqual(info['developer_familiarity_overall'], 0)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 0)
        self.assertEqual(info['reviewer_familiarity_overall'], 11)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 4)
        self.assertGreaterEqual(info['crashes'], 0)

        # IRC handle first character is lower case in Mercurial, upper case in Bugzilla.
        info = patchanalysis.bug_analysis(799266)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 0)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 28)
        self.assertEqual(info['changes_size'], 104)
        self.assertEqual(info['test_changes_size'], 0)
        self.assertEqual(info['modules_num'], 1)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 355)
        self.assertEqual(info['code_churn_last_3_releases'], 37)
        self.assertEqual(info['developer_familiarity_overall'], 36)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 5)
        self.assertEqual(info['reviewer_familiarity_overall'], 1)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 0)
        self.assertGreaterEqual(info['crashes'], 0)

        # r=IRC_HANDLE_OF_THE_AUTHOR
        info = patchanalysis.bug_analysis(721760)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 0)
        self.assertEqual(info['depends_on'], 1)
        self.assertEqual(info['comments'], 72)
        self.assertEqual(info['changes_size'], 216)
        self.assertEqual(info['test_changes_size'], 0)
        self.assertEqual(info['modules_num'], 2)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 38)
        self.assertEqual(info['code_churn_last_3_releases'], 25)
        self.assertEqual(info['developer_familiarity_overall'], 28)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 17)
        self.assertEqual(info['reviewer_familiarity_overall'], 13)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 6)
        self.assertGreaterEqual(info['crashes'], 0)

        # IRC handle is ':IRC_HANDLE.SURNAME' and reviewer is not a reviewer of the patch on Bugzilla.
        info = patchanalysis.bug_analysis(1021265)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 3)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 111)
        self.assertEqual(info['changes_size'], 173)
        self.assertEqual(info['test_changes_size'], 0)
        self.assertEqual(info['modules_num'], 5)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 1763)
        self.assertEqual(info['code_churn_last_3_releases'], 150)
        self.assertEqual(info['developer_familiarity_overall'], 66)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 17)
        self.assertEqual(info['reviewer_familiarity_overall'], 325)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 36)
        self.assertGreaterEqual(info['crashes'], 0)

        # IRC handle is the beginning of the real name with a space after.
        info = patchanalysis.bug_analysis(1029098)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 1)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 15)
        self.assertEqual(info['changes_size'], 94)
        self.assertEqual(info['test_changes_size'], 97)
        self.assertEqual(info['modules_num'], 1)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 277)
        self.assertEqual(info['code_churn_last_3_releases'], 15)
        self.assertEqual(info['developer_familiarity_overall'], 81)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 8)
        self.assertEqual(info['reviewer_familiarity_overall'], 9)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 0)
        self.assertGreaterEqual(info['crashes'], 0)

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
        self.assertEqual(info['changes_size'], 148)
        self.assertEqual(info['test_changes_size'], 0)
        self.assertEqual(info['modules_num'], 2)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 887)
        self.assertEqual(info['code_churn_last_3_releases'], 149)
        self.assertEqual(info['developer_familiarity_overall'], 131)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 19)
        self.assertEqual(info['reviewer_familiarity_overall'], 7)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 7)
        self.assertGreaterEqual(info['crashes'], 0)

        # r=backout
        info = patchanalysis.bug_analysis(679509)
        self.assertEqual(info['backout_num'], 0)
        self.assertEqual(info['blocks'], 0)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 97)
        self.assertEqual(info['changes_size'], 347)
        self.assertEqual(info['test_changes_size'], 108)
        self.assertEqual(info['modules_num'], 5)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 1874)
        self.assertEqual(info['code_churn_last_3_releases'], 334)
        self.assertEqual(info['developer_familiarity_overall'], 116)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 43)
        self.assertEqual(info['reviewer_familiarity_overall'], 53)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 44)
        self.assertGreaterEqual(info['crashes'], 0)

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

        # Check uplift request
        info = patchanalysis.bug_analysis(1230065)

        self.assertIsNotNone(info['uplift_comment'])
        self.assertEqual(len(info['uplift_comment']['text'].split('\n')), 11)
        self.assertEqual(info['uplift_comment']['id'], 11222288)
        self.assertIsNotNone(info['uplift_author'])
        self.assertEqual(info['uplift_author']['email'], 'karlt@mozbugz.karlt.net')

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
