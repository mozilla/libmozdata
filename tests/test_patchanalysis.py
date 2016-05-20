# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
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
        self.assertTrue(info['code_churn_overall'] >= 182)
        self.assertTrue(info['code_churn_last_3_releases'] >= 0)

        info = patchanalysis.bug_analysis(737976)
        self.assertEqual(info['backout_num'], 2)
        self.assertEqual(info['blocks'], 1)
        self.assertEqual(info['depends_on'], 1)
        self.assertEqual(info['comments'], 12)
        self.assertEqual(info['changes_size'], 14489)
        self.assertEqual(info['modules_num'], 12)
        self.assertEqual(info['r-ed_patches'], 1)
        self.assertTrue(info['code_churn_overall'] >= 11564)
        self.assertTrue(info['code_churn_last_3_releases'] >= 0)

        info = patchanalysis.bug_analysis(1271794)
        self.assertEqual(info['backout_num'], 1)
        self.assertEqual(info['blocks'], 1)
        self.assertEqual(info['depends_on'], 2)
        self.assertEqual(info['comments'], 23)
        self.assertEqual(info['changes_size'], 76)
        self.assertEqual(info['modules_num'], 3)
        self.assertEqual(info['r-ed_patches'], 0)
        self.assertTrue(info['code_churn_overall'] >= 125)
        self.assertTrue(info['code_churn_last_3_releases'] >= 0)

if __name__ == '__main__':
    unittest.main()
