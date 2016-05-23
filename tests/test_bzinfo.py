# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from clouseau.BZInfo import BZInfo


class BZInfoTest(unittest.TestCase):

    def test_bzinfo(self):
        info = BZInfo(12345).get()

        self.assertTrue('12345' in info)
        info = info['12345']
        self.assertTrue(info['authorized'])
        self.assertEqual(info['owner'], u'jefft@formerly-netscape.com.tld')
        self.assertTrue(u'jefft@formerly-netscape.com.tld' in info['commenters'])
        self.assertEqual(info['component'], 'Backend')
        self.assertEqual(info['product'], 'MailNews Core')

    def test_bzinfo_unauthorized(self):
        bzi = BZInfo(1269839)

        info = bzi.get()

        self.assertTrue('1269839' in info)
        info = info['1269839']
        self.assertFalse(info['authorized'])
        self.assertEqual(info['ownership'], [])
        self.assertEqual(info['commenters'], {})
        self.assertEqual(info['reviewers'], set())

        self.assertIsNone(bzi.get_best_collaborator())
        self.assertIsNone(bzi.get_best_component_product())

if __name__ == '__main__':
    unittest.main()
