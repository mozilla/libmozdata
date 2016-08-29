# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import responses
from libmozdata.CrashInfo import CrashInfo
from libmozdata.socorro import SuperSearch
from tests.auto_mock import MockTestCase


class CrashInfoTest(MockTestCase):

    mock_urls = [
        SuperSearch.URL,
    ]

    @responses.activate
    def test_single(self):
        path = 'toolkit/components/terminator/nsterminator.cpp'

        ci = CrashInfo(path).get()

        self.assertEqual(ci[path], 144280)

    @responses.activate
    def test_multiple(self):
        path1 = 'toolkit/components/terminator/nsterminator.cpp'
        path2 = 'gfx/layers/d3d11/textured3d11.cpp'

        ci = CrashInfo([path1, path2]).get()

        self.assertEqual(ci[path1], 144280)
        self.assertEqual(ci[path2], 8991)

    @responses.activate
    def test_not_lower(self):
        path = 'toolkit/components/terminator/nsTerminator.cpp'

        ci = CrashInfo(path).get()
        ci2 = CrashInfo(path.lower()).get()

        self.assertEqual(ci[path], ci2[path.lower()])

    @responses.activate
    def test_basename(self):
        path = 'toolkit/components/terminator/nsTerminator.cpp'

        ci = CrashInfo(path).get()
        ci2 = CrashInfo(os.path.basename(path)).get()

        self.assertEqual(ci[path], ci2[os.path.basename(path)])

    @responses.activate
    def test_empty_array(self):
        self.assertEqual(CrashInfo([]).get(), {})
