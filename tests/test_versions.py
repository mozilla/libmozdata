# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import unittest
from contextlib import contextmanager

import responses
from dateutil.tz import tzutc

import libmozdata.utils as utils
import libmozdata.versions as versions


class VersionsTest(unittest.TestCase):
    def cleanup(self):
        """
        Restore versions from cache after this test
        Otherwise other tests will use the last loaded version
        """
        versions.__dict__["__versions"] = None

    def tearDown(self):
        self.cleanup()

    @contextmanager
    def setup_versions(self, stable, devel, nightly, esr, esr_next=None):
        """
        Add a mock response for official versions
        """
        self.cleanup()
        body = {
            "FIREFOX_NIGHTLY": nightly,
            "FIREFOX_ESR": esr,
            "FIREFOX_ESR_NEXT": esr_next,
            "LATEST_FIREFOX_DEVEL_VERSION": devel,
            "LATEST_FIREFOX_OLDER_VERSION": "3.6.28",
            "LATEST_FIREFOX_RELEASED_DEVEL_VERSION": devel,
            "LATEST_FIREFOX_VERSION": stable,
        }
        local_mock = responses.RequestsMock()
        local_mock.add(responses.GET, versions.URL_VERSIONS, json=body)
        local_mock.start()
        yield local_mock
        local_mock.stop()

    def test_versions(self):
        v = versions.get(base=True)
        self.assertTrue(v["esr"] <= v["release"] <= v["beta"] <= v["nightly"])

    def test_version_dates(self):
        self.assertEqual(
            versions.getMajorDate(46),
            datetime.datetime(2016, 4, 26, 7, 0, tzinfo=tzutc()),
        )
        self.assertEqual(
            versions.getMajorDate("46"),
            datetime.datetime(2016, 4, 26, 7, 0, tzinfo=tzutc()),
        )
        self.assertEqual(
            versions.getMajorDate("46.0"),
            datetime.datetime(2016, 4, 26, 7, 0, tzinfo=tzutc()),
        )
        self.assertEqual(
            versions.getMajorDate("46.0.1"),
            datetime.datetime(2016, 4, 26, 7, 0, tzinfo=tzutc()),
        )
        self.assertEqual(
            versions.getMajorDate("1"),
            datetime.datetime(2004, 11, 9, 8, 0, tzinfo=tzutc()),
        )
        self.assertEqual(
            versions.getMajorDate("1.0"),
            datetime.datetime(2004, 11, 9, 8, 0, tzinfo=tzutc()),
        )
        self.assertEqual(
            versions.getMajorDate("1.5"),
            datetime.datetime(2005, 11, 29, 8, 0, tzinfo=tzutc()),
        )
        self.assertEqual(
            versions.getMajorDate("14"),
            datetime.datetime(2012, 7, 17, 7, 0, tzinfo=tzutc()),
        )
        self.assertEqual(
            versions.getMajorDate("14.0"),
            datetime.datetime(2012, 7, 17, 7, 0, tzinfo=tzutc()),
        )
        self.assertEqual(
            versions.getMajorDate("14.0.1"),
            datetime.datetime(2012, 7, 17, 7, 0, tzinfo=tzutc()),
        )
        self.assertEqual(
            versions.getMajorDate("33"),
            datetime.datetime(2014, 10, 14, 7, 0, tzinfo=tzutc()),
        )
        self.assertEqual(
            versions.getMajorDate("33.0"),
            datetime.datetime(2014, 10, 14, 7, 0, tzinfo=tzutc()),
        )
        self.assertEqual(
            versions.getMajorDate("33.1"),
            datetime.datetime(2014, 11, 10, 8, 0, tzinfo=tzutc()),
        )

        self.assertEqual(versions.getMajorDate("46"), versions.getDate("46"))
        self.assertEqual(versions.getMajorDate("46.0"), versions.getDate("46.0"))
        self.assertNotEqual(versions.getMajorDate("48.0"), versions.getDate("48.0.1"))
        self.assertEqual(
            versions.getDate("48.0.1"),
            datetime.datetime(2016, 8, 18, 7, 0, tzinfo=tzutc()),
        )
        self.assertEqual(
            versions.getDate("48.0.2"),
            datetime.datetime(2016, 8, 24, 7, 0, tzinfo=tzutc()),
        )

        v = versions.get(base=True)
        if versions.getMajorDate(v["nightly"]) is not None:
            self.assertTrue(
                versions.getMajorDate(v["release"])
                <= versions.getMajorDate(v["beta"])
                <= versions.getMajorDate(v["nightly"])
            )
        elif versions.getMajorDate(v["beta"]) is not None:
            self.assertTrue(
                versions.getMajorDate(v["release"]) <= versions.getMajorDate(v["beta"])
            )

        date = utils.get_date_ymd("2011-08-24T14:52:52Z")
        self.assertEqual(
            date - versions.getMajorDate("7"), datetime.timedelta(-34, 28372)
        )

        self.assertEqual(
            versions.getCloserMajorRelease(date),
            ("7.0", datetime.datetime(2011, 9, 27, 7, 0, tzinfo=tzutc())),
        )
        self.assertEqual(
            versions.getCloserMajorRelease(date, negative=True),
            ("6.0", datetime.datetime(2011, 8, 16, 7, 0, tzinfo=tzutc())),
        )
        self.assertEqual(
            versions.getCloserMajorRelease(date, negative=False),
            ("7.0", datetime.datetime(2011, 9, 27, 7, 0, tzinfo=tzutc())),
        )

        date = utils.get_date_ymd("2016-08-19")
        self.assertEqual(
            versions.getCloserRelease(date),
            ("48.0.2", datetime.datetime(2016, 8, 24, 7, 0, tzinfo=tzutc())),
        )
        self.assertEqual(
            versions.getCloserRelease(date, negative=True),
            ("48.0.1", datetime.datetime(2016, 8, 18, 7, 0, tzinfo=tzutc())),
        )
        self.assertEqual(
            versions.getCloserRelease(date, negative=False),
            ("48.0.2", datetime.datetime(2016, 8, 24, 7, 0, tzinfo=tzutc())),
        )

    def test_dual_esr(self):
        # Check esr & esr previous
        with self.setup_versions(
            nightly="55.0a1",
            devel="54.0b6",
            stable="53.0.2",
            esr="45.9.0esr",
            esr_next="52.1.1esr",
        ):
            v = versions.get(base=True)
        self.assertDictEqual(
            v, {"nightly": 55, "beta": 54, "release": 53, "esr": 52, "esr_previous": 45}
        )

    def test_unique_esr(self):
        # Check no esr previous is present
        with self.setup_versions(
            nightly="55.0a1", devel="54.0b6", stable="53.0.2", esr="52.1.1esr"
        ):
            v = versions.get(base=True)
        self.assertDictEqual(
            v,
            {"nightly": 55, "beta": 54, "release": 53, "esr": 52, "esr_previous": None},
        )


if __name__ == "__main__":
    unittest.main()
