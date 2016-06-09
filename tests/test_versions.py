# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import datetime
from dateutil.tz import tzutc
import clouseau.utils as utils
import clouseau.versions as versions


class VersionsTest(unittest.TestCase):

    def test_versions(self):
        v = versions.get(base=True)
        self.assertTrue(v['release'] <= v['beta'] < v['aurora'] < v['nightly'])

    def test_version_dates(self):
        self.assertEqual(versions.getMajorDate(46), datetime.datetime(2016, 4, 26, 0, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('46'), datetime.datetime(2016, 4, 26, 0, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('46.0'), datetime.datetime(2016, 4, 26, 0, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('46.0.1'), datetime.datetime(2016, 4, 26, 0, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('1'), datetime.datetime(2004, 11, 9, 0, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('1.0'), datetime.datetime(2004, 11, 9, 0, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('1.0'), datetime.datetime(2004, 11, 9, 0, 0, tzinfo=tzutc()))

        date = utils.get_date_ymd('2011-08-24T14:52:52Z')
        self.assertEqual(date - versions.getMajorDate('7'), datetime.timedelta(-34, 53572))

if __name__ == '__main__':
    unittest.main()
