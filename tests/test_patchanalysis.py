# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import warnings
from clouseau.bugzilla import Bugzilla
from clouseau import patchanalysis


class PatchAnalysisTest(unittest.TestCase):

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
        self.assertGreater(info['crashes'], 0)

        bug = {}

        def bughandler(found_bug, data):
            bug.update(found_bug)

        def commenthandler(found_bug, bugid, data):
            bug['comments'] = found_bug['comments']

        def attachmenthandler(attachments, bugid, data):
            bug['attachments'] = attachments

        Bugzilla('id=547914', bughandler=bughandler, commenthandler=commenthandler, attachmenthandler=attachmenthandler).get_data().wait()

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
            self.assertEqual(len(w), 2)
            self.assertTrue(str(w[0].message) == 'Revision d0ab0d508a24 was not found.' or str(w[1].message) == 'Revision d0ab0d508a24 was not found.')
            self.assertTrue(str(w[0].message) == 'Revision 9f4983dfd881 was not found.' or str(w[1].message) == 'Revision 9f4983dfd881 was not found.')
            self.assertEqual(info['backout_num'], 1)
            self.assertEqual(info['blocks'], 1)
            self.assertEqual(info['depends_on'], 2)
            self.assertEqual(info['comments'], 24)
            self.assertEqual(info['changes_size'], 76)
            self.assertEqual(info['test_changes_size'], 0)
            self.assertEqual(info['modules_num'], 3)
            self.assertEqual(info['r-ed_patches'], 0)
            self.assertEqual(info['code_churn_overall'], 246)
            self.assertEqual(info['code_churn_last_3_releases'], 242)
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
        self.assertEqual(info['blocks'], 5)
        self.assertEqual(info['depends_on'], 34)
        self.assertEqual(info['comments'], 101)
        self.assertEqual(info['changes_size'], 2752)
        self.assertEqual(info['test_changes_size'], 462)
        self.assertEqual(info['modules_num'], 11)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertEqual(info['code_churn_overall'], 8178)
        self.assertEqual(info['code_churn_last_3_releases'], 788)
        self.assertEqual(info['developer_familiarity_overall'], 162)
        self.assertEqual(info['developer_familiarity_last_3_releases'], 51)
        self.assertEqual(info['reviewer_familiarity_overall'], 2)
        self.assertEqual(info['reviewer_familiarity_last_3_releases'], 0)
        self.assertGreater(info['crashes'], 0)

        # Custom backout (no reference to revision).
        # Author has a different name on Bugzilla and Mercurial and they don't use the email on Mercurial.
        with warnings.catch_warnings(record=True) as w:
            info = patchanalysis.bug_analysis(1220307)
            self.assertEqual(len(w), 2)
            self.assertEqual(str(w[0].message), 'Looks like a backout, but we couldn\'t find which revision was backed out.')
            self.assertEqual(str(w[1].message), 'Revision da10eecd0e76 is related to another bug (1276850).')
            self.assertEqual(info['backout_num'], 2)
            self.assertEqual(info['blocks'], 4)
            self.assertEqual(info['depends_on'], 1)
            self.assertEqual(info['comments'], 42)
            self.assertEqual(info['changes_size'], 67)
            self.assertEqual(info['test_changes_size'], 50)
            self.assertEqual(info['modules_num'], 3)
            self.assertEqual(info['r-ed_patches'], 0)
            self.assertEqual(info['code_churn_overall'], 77)
            self.assertEqual(info['code_churn_last_3_releases'], 31)
            self.assertEqual(info['developer_familiarity_overall'], 5)
            self.assertEqual(info['developer_familiarity_last_3_releases'], 5)
            self.assertEqual(info['reviewer_familiarity_overall'], 2)
            self.assertEqual(info['reviewer_familiarity_last_3_releases'], 1)
            self.assertGreater(info['crashes'], 0)

        with warnings.catch_warnings(record=True) as w:
            info = patchanalysis.bug_analysis(1276850)
            self.assertEqual(len(w), 1)
            self.assertEqual(str(w[0].message), 'Looks like a backout, but we couldn\'t find which revision was backed out.')
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
            self.assertEqual(len(w), 1)
            self.assertEqual(str(w[0].message), 'Revision 8de609c5d378 is related to another bug (743252).')
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
        # Disable because it's too slow for tests.
        # info = patchanalysis.bug_analysis(914034)
        # self.assertEqual(info['backout_num'], 0)
        # self.assertEqual(info['blocks'], 2)
        # self.assertEqual(info['depends_on'], 1)
        # self.assertEqual(info['comments'], 26)
        # self.assertEqual(info['changes_size'], 93872)
        # self.assertEqual(info['test_changes_size'], 1488)
        # self.assertEqual(info['modules_num'], 23)
        # self.assertEqual(info['r-ed_patches'], 0)
        # self.assertEqual(info['code_churn_overall'], 18959)
        # self.assertEqual(info['code_churn_last_3_releases'], 2396)
        # self.assertEqual(info['developer_familiarity_overall'], 151)
        # self.assertEqual(info['developer_familiarity_last_3_releases'], 54)
        # self.assertEqual(info['reviewer_familiarity_overall'], 18722)
        # self.assertEqual(info['reviewer_familiarity_last_3_releases'], 2371)
        # self.assertGreaterEqual(info['crashes'], 0)

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

if __name__ == '__main__':
    unittest.main()
