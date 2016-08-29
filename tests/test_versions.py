# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import datetime
from dateutil.tz import tzutc
import libmozdata.utils as utils
import libmozdata.versions as versions


class VersionsTest(unittest.TestCase):

    def test_versions(self):
        v = versions.get(base=True)
        self.assertTrue(v['esr'] <= v['release'] <= v['beta'] < v['aurora'] < v['nightly'])

    def test_version_dates(self):
        self.assertEqual(versions.getMajorDate(46), datetime.datetime(2016, 4, 26, 7, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('46'), datetime.datetime(2016, 4, 26, 7, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('46.0'), datetime.datetime(2016, 4, 26, 7, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('46.0.1'), datetime.datetime(2016, 4, 26, 7, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('1'), datetime.datetime(2004, 11, 9, 8, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('1.0'), datetime.datetime(2004, 11, 9, 8, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('1.5'), datetime.datetime(2005, 11, 29, 8, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('14'), datetime.datetime(2012, 7, 17, 7, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('14.0'), datetime.datetime(2012, 7, 17, 7, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('14.0.1'), datetime.datetime(2012, 7, 17, 7, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('33'), datetime.datetime(2014, 10, 14, 7, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('33.0'), datetime.datetime(2014, 10, 14, 7, 0, tzinfo=tzutc()))
        self.assertEqual(versions.getMajorDate('33.1'), datetime.datetime(2014, 11, 10, 8, 0, tzinfo=tzutc()))

        v = versions.get(base=True)
        self.assertTrue(versions.getMajorDate(v['release']) <= versions.getMajorDate(v['beta']) <= versions.getMajorDate(v['aurora']) <= versions.getMajorDate(v['nightly']))

        date = utils.get_date_ymd('2011-08-24T14:52:52Z')
        self.assertEqual(date - versions.getMajorDate('7'), datetime.timedelta(-34, 28372))

        self.assertEqual(versions.getCloserMajorRelease(date), ('7.0', datetime.datetime(2011, 9, 27, 7, 0, tzinfo=tzutc())))
        self.assertEqual(versions.getCloserMajorRelease(date, negative=True), ('6.0', datetime.datetime(2011, 8, 16, 7, 0, tzinfo=tzutc())))
        self.assertEqual(versions.getCloserMajorRelease(date, negative=False), ('7.0', datetime.datetime(2011, 9, 27, 7, 0, tzinfo=tzutc())))

if __name__ == '__main__':
    unittest.main()
