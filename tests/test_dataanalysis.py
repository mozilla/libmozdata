# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from libmozdata.bugzilla import Bugzilla
from libmozdata.socorro import Socorro
from libmozdata.hgmozilla import Mercurial
from libmozdata import dataanalysis
from libmozdata import utils
from tests.auto_mock import MockTestCase
import responses


class DataAnalysisTest(MockTestCase):
    mock_urls = [
        Bugzilla.URL,
        Socorro.CRASH_STATS_URL,
        Mercurial.HG_URL,
    ]

    @responses.activate
    def test_bug_analysis(self):
        info = dataanalysis.analyze_bugs(['1270686'],
                                         minimal_releases={'nightly': -1, 'aurora': -1, 'beta': 1, 'release': 1},
                                         minimal_days={'nightly': 3, 'aurora': 3, 'beta': -1, 'release': 7})
        self.assertEqual(list(info.keys()), ['1270686'])
        info = info['1270686']
        self.assertEqual(info['affected'], set())
        self.assertEqual(info['approval'], {'aurora', 'beta'})
        self.assertEqual(info['land']['aurora'], utils.get_date_ymd('2016-05-31 14:20:34'))
        self.assertEqual(info['land']['beta'], utils.get_date_ymd('2016-05-26 21:02:09'))
        self.assertEqual(info['land']['nightly'], utils.get_date_ymd('2016-05-31 10:00:19'))
        self.assertEqual(info['signatures'], ['TppTimerpExecuteCallback'])
        stops = info['stops']['TppTimerpExecuteCallback']
        self.assertEqual(stops['aurora'], 'yes')
        self.assertEqual(stops['beta'], 'yes')
        self.assertEqual(stops['nightly'], 'yes')


if __name__ == '__main__':
    unittest.main()
