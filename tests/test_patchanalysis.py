# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
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
        self.assertEqual(info['modules_num'], 1)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertGreaterEqual(info['code_churn_overall'], 182)
        self.assertGreaterEqual(info['code_churn_last_3_releases'], 0)
        self.assertGreaterEqual(info['developer_familiarity_overall'], 55)
        self.assertGreaterEqual(info['developer_familiarity_last_3_releases'], 0)
        self.assertGreater(info['crashes'], 0)

        info = patchanalysis.bug_analysis(647570)
        self.assertEqual(info['backout_num'], 1)
        self.assertEqual(info['blocks'], 3)
        self.assertEqual(info['depends_on'], 0)
        self.assertEqual(info['comments'], 40)
        self.assertEqual(info['changes_size'], 485)
        self.assertEqual(info['modules_num'], 3)
        self.assertEqual(info['r-ed_patches'], 3)
        self.assertGreaterEqual(info['code_churn_overall'], 240)
        self.assertGreaterEqual(info['code_churn_last_3_releases'], 0)
        self.assertGreaterEqual(info['developer_familiarity_overall'], 10)
        self.assertGreaterEqual(info['developer_familiarity_last_3_releases'], 0)
        self.assertGreater(info['crashes'], 0)

        info = patchanalysis.bug_analysis(1271794)
        self.assertEqual(info['backout_num'], 1)
        self.assertEqual(info['blocks'], 1)
        self.assertEqual(info['depends_on'], 2)
        self.assertEqual(info['comments'], 24)
        self.assertEqual(info['changes_size'], 76)
        self.assertEqual(info['modules_num'], 3)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertGreaterEqual(info['code_churn_overall'], 125)
        self.assertGreaterEqual(info['code_churn_last_3_releases'], 0)
        self.assertGreaterEqual(info['developer_familiarity_overall'], 0)
        self.assertGreaterEqual(info['developer_familiarity_last_3_releases'], 0)
        self.assertGreaterEqual(info['crashes'], 0)

        # Test mozreview patch caching.
        info2 = patchanalysis.bug_analysis(1271794)
        self.assertEqual(info2, info)

        bug = {}

        def bughandler(found_bug, data):
            bug.update(found_bug)

        def commenthandler(found_bug, bugid, data):
            bug['comments'] = found_bug['comments']

        def attachmenthandler(attachments, bugid, data):
            bug['attachments'] = attachments

        Bugzilla('id=1271794', bughandler=bughandler, commenthandler=commenthandler, attachmenthandler=attachmenthandler).get_data().wait()

        info3 = patchanalysis.bug_analysis(bug)
        self.assertEqual(info3, info)

if __name__ == '__main__':
    unittest.main()
