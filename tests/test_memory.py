# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from libmozdata import memory


class MemoryTest(unittest.TestCase):

    def test_isweird(self):
        self.assertTrue(memory.isweird('0x0', '64'))
        self.assertTrue(memory.isweird('0x0', '32'))
        self.assertTrue(memory.isweird('0xAAA', '64'))
        self.assertTrue(memory.isweird('0xAAA', '32'))
        self.assertTrue(memory.isweird('0xaaa', '64'))
        self.assertTrue(memory.isweird('0xaaa', '32'))
        self.assertTrue(memory.isweird('0xffff', '64'))
        self.assertTrue(memory.isweird('0xffff', '32'))
        self.assertFalse(memory.isweird('0xdeadbeef', '64'))
        self.assertFalse(memory.isweird('0xdeadbeef', '32'))
        self.assertFalse(memory.isweird('0xAAAAAAAAAAAB0000', '64'))
        self.assertFalse(memory.isweird('0xfffffffffffB0000', '64'))
        self.assertTrue(memory.isweird('0xffffffffffff0000', '64'))
        self.assertTrue(memory.isweird('0xffff0000', '32'))
        self.assertTrue(memory.isweird('0xffffffffffffaaaa', '64'))
        self.assertTrue(memory.isweird('0xffffaaaa', '32'))
        self.assertTrue(memory.isweird('0x000000000000ffff', '64'))
        self.assertTrue(memory.isweird('0x0000ffff', '32'))

        with self.assertRaises(Exception):
            self.assertTrue(memory.isweird(None, '64'))
        with self.assertRaises(Exception):
            self.assertTrue(memory.isweird(42, '32'))

if __name__ == '__main__':
    unittest.main()
