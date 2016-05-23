# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import unittest
from clouseau.CrashInfo import CrashInfo


class CrashInfoTest(unittest.TestCase):

    def test_single(self):
        path = 'toolkit/components/terminator/nsterminator.cpp'

        ci = CrashInfo(path).get()

        self.assertGreaterEqual(ci[path]['crashes'], 189102)

    def test_multiple(self):
        path1 = 'toolkit/components/terminator/nsterminator.cpp'
        path2 = 'gfx/layers/d3d11/textured3d11.cpp'

        ci = CrashInfo([path1, path2]).get()

        self.assertGreaterEqual(ci[path1]['crashes'], 189102)
        self.assertGreaterEqual(ci[path2]['crashes'], 9850)

    def test_not_lower(self):
        path = 'toolkit/components/terminator/nsTerminator.cpp'

        ci = CrashInfo(path).get()
        ci2 = CrashInfo(path.lower()).get()

        self.assertEqual(ci[path]['crashes'], ci2[path.lower()]['crashes'])

    def test_basename(self):
        path = 'toolkit/components/terminator/nsTerminator.cpp'

        ci = CrashInfo(path).get()
        ci2 = CrashInfo(os.path.basename(path)).get()

        self.assertEqual(ci[path]['crashes'], ci2[os.path.basename(path)]['crashes'])
