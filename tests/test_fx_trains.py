# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import responses

from libmozdata.fx_trains import FirefoxTrains
from tests.auto_mock import MockTestCase


class FirefoxTrainsTest(MockTestCase):
    mock_urls = [FirefoxTrains.URL]

    @responses.activate
    def test_get_release_owners(self):
        fx_trains = FirefoxTrains()
        release_owner = fx_trains.get_release_owners()
        self.assertEqual(release_owner["29"], "Sylvestre Ledru")

    @responses.activate
    def test_get_firefox_releases(self):
        fx_trains = FirefoxTrains()
        release_dates = fx_trains.get_firefox_releases()
        self.assertEqual(release_dates["29.0"], "2014-04-29")

    @responses.activate
    def test_get_release_schedule(self):
        fx_trains = FirefoxTrains()
        release_schedule = fx_trains.get_release_schedule("beta")
        self.assertIn("nightly_start", release_schedule)

    @responses.activate
    def test_caching(self):
        fx_trains_1 = FirefoxTrains.get_instance()
        fx_trains_2 = FirefoxTrains.get_instance()
        self.assertIs(fx_trains_1, fx_trains_2)

        resp_1 = fx_trains_1.get_release_schedule("beta")
        resp_2 = fx_trains_2.get_release_schedule("beta")
        self.assertIs(resp_1, resp_2)

        # No caching across instances.
        fx_trains_3 = FirefoxTrains()
        fx_trains_4 = FirefoxTrains()
        self.assertIsNot(fx_trains_3, fx_trains_4)

        resp_3 = fx_trains_3.get_release_schedule("beta")
        resp_4 = fx_trains_4.get_release_schedule("beta")
        self.assertIsNot(resp_3, resp_4)
