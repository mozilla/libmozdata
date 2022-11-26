# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

from libmozdata.fx_trains import FirefoxTrains


class FirefoxTrainsTest(unittest.TestCase):
    def test_get_release_owners(self):
        fx_trains = FirefoxTrains()
        release_owner = fx_trains.get_release_owners()
        self.assertEqual(release_owner["29"], "Sylvestre Ledru")

    def test_get_firefox_releases(self):
        fx_trains = FirefoxTrains()
        release_dates = fx_trains.get_firefox_releases()
        self.assertEqual(release_dates["29.0"], "2014-04-29")

    def test_get_release_schedule(self):
        fx_trains = FirefoxTrains()
        release_schedule = fx_trains.get_release_schedule("beta")
        self.assertIn("nightly_start", release_schedule)
