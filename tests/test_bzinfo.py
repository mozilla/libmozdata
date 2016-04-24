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


if __name__ == '__main__':
    unittest.main()
