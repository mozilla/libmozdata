# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import math
import time
import unittest

from dateutil.tz import tzutc

from libmozdata import utils


class UtilsTest(unittest.TestCase):
    def test_get_best(self):
        self.assertIsNone(utils.get_best(None))
        self.assertIsNone(utils.get_best({}))
        self.assertEqual(utils.get_best({"key1": 7, "key2": 99, "key3": 4}), "key2")

    def test_get_timestamp(self):
        date = "1991-04-16"
        self.assertEqual(utils.get_timestamp(date), 671760000)
        self.assertEqual(
            utils.get_timestamp(datetime.datetime.strptime(date, "%Y-%m-%d")), 671760000
        )
        self.assertGreater(utils.get_timestamp("today"), utils.get_timestamp(date))
        ts1 = utils.get_timestamp("now")
        time.sleep(1.01)
        ts2 = utils.get_timestamp("now")
        self.assertGreater(ts2, ts1)

    def test_get_date_ymd(self):
        self.assertIsNotNone(utils.get_date_ymd("today"))
        self.assertIsNotNone(utils.get_date_ymd("yesterday"))
        self.assertIsNotNone(utils.get_date_ymd("tomorrow"))
        self.assertTrue(
            utils.get_date_ymd("yesterday")
            < utils.get_date_ymd("today")
            < utils.get_date_ymd("tomorrow")
        )
        date = utils.as_utc(datetime.datetime.strptime("1991-04-16", "%Y-%m-%d"))
        self.assertEqual(utils.get_date_ymd("1991/04/16"), date)
        self.assertEqual(utils.get_date_ymd("1991-04-16"), date)
        self.assertEqual(utils.get_date_ymd("1991 04 16"), date)
        self.assertEqual(utils.get_date_ymd("04/16/1991"), date)
        self.assertEqual(utils.get_date_ymd("16/04/1991"), date)
        self.assertEqual(
            utils.get_date_ymd("1991-04-16 12:00:00"),
            utils.as_utc(datetime.datetime(1991, 4, 16, 12, 0)),
        )

        with self.assertRaises(Exception):
            utils.get_date_ymd("")
        with self.assertRaises(Exception):
            utils.get_date_ymd("marco")

    def test_get_today(self):
        self.assertIsNotNone(utils.get_today())

    def test_get_date_str(self):
        date = "1991-04-16"
        self.assertEqual(
            utils.get_date_str(datetime.datetime.strptime(date, "%Y-%m-%d")), date
        )

    def test_get_date(self):
        self.assertEqual(utils.get_date("1991/04/16"), "1991-04-16")
        self.assertEqual(utils.get_date("1991/04/16", 1), "1991-04-15")

    def test_get_now_timestamp(self):
        date = "1991-04-16"
        self.assertGreater(utils.get_now_timestamp(), utils.get_timestamp(date))

    def test_date_from_timestamp(self):
        date = "1975-03-16"
        dt = utils.get_date_ymd(date)
        ts = utils.get_timestamp(dt)
        self.assertEqual(dt, datetime.datetime(1975, 3, 16, tzinfo=tzutc()))
        self.assertEqual(ts, 164160000)
        new_dt = utils.get_date_from_timestamp(ts)
        self.assertEqual(new_dt, dt)

    def test_is64(self):
        self.assertTrue(utils.is64("64bit"))
        self.assertTrue(utils.is64("A 64 bit machine"))
        self.assertFalse(utils.is64("A 32 bit machine"))

    def test_percent(self):
        self.assertEqual(utils.percent(0.23), "23%")
        self.assertEqual(utils.percent(1), "100%")
        self.assertEqual(utils.percent(1.5), "150%")

    def test_simple_percent(self):
        self.assertEqual(utils.simple_percent(3), "3%")
        self.assertEqual(utils.simple_percent(3.0), "3%")
        self.assertEqual(utils.simple_percent(3.5), "3.5%")

    def test_get_sample(self):
        arr = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.assertEqual(utils.get_sample(arr, -7), arr)
        self.assertEqual(utils.get_sample(arr, 0), [])
        self.assertEqual(utils.get_sample(arr, 1), arr)
        self.assertEqual(utils.get_sample(arr, 7), arr)
        self.assertEqual(len(utils.get_sample(arr, 0.1)), 1)

    def test_get_date_from_buildid(self):
        self.assertEqual(
            utils.get_date_from_buildid("20160407164938"),
            datetime.datetime(2016, 4, 7, 23, 49, 38, tzinfo=tzutc()),
        )
        self.assertEqual(
            utils.get_date_from_buildid(20160407164938),
            datetime.datetime(2016, 4, 7, 23, 49, 38, tzinfo=tzutc()),
        )

    def test_rate(self):
        self.assertEqual(utils.rate(1.0, 2.0), 0.5)
        self.assertEqual(utils.rate(0.0, 2.0), 0.0)
        self.assertTrue(math.isnan(utils.rate(1.0, 0.0)))
        self.assertTrue(math.isnan(utils.rate(0.0, 0.0)))

    def test_uplift_comment_html(self):
        import glob

        from libmozdata.patchanalysis import parse_uplift_comment as parse

        # Bugzilla bug
        out = parse("This is about bUg 12345. What a great bug.")
        self.assertEqual(
            out,
            '<div class="no-header">This is about <a href="https://bugzilla.mozilla.org/12345" target="_blank">Bug 12345</a>. What a great bug.</div>',
        )

        # Simple link
        out = parse("http://mozilla.org")
        self.assertEqual(
            out,
            '<div class="no-header"><a href="http://mozilla.org" target="_blank">http://mozilla.org</a></div>',
        )

        # Complex link
        out = parse(
            "https://developer.mozilla.org/en-US/docs/Web/API/Media_Streams_API/Constraints#Result"
        )
        self.assertEqual(
            out,
            '<div class="no-header"><a href="https://developer.mozilla.org/en-US/docs/Web/API/Media_Streams_API/Constraints#Result" target="_blank">https://developer.mozilla.org/en-US/docs/Web/API/Media_Streams_API/Constraints#Result</a></div>',
        )

        # Html escaped
        out = parse("Bug on <select/> element")
        self.assertEqual(
            out, '<div class="no-header">Bug on &lt;select/&gt; element</div>'
        )

        # Risky "risks and why"
        out = parse("[Risks and why]: Medium.")
        self.assertEqual(
            out,
            '<h1 class="risks-and-why risky">Risks and why</h1><div class="risks-and-why risky">Medium.</div>',
        )

        # Risky string change
        out = parse("[String/UUID change made/needed]: yes, we need a change")
        self.assertEqual(
            out,
            '<h1 class="string-uuid-change risky">String/UUID change made/needed</h1><div class="string-uuid-change risky">yes, we need a change</div>',
        )
        out = parse("[String/UUID change made/needed]: N/A")
        self.assertEqual(
            out,
            '<h1 class="string-uuid-change">String/UUID change made/needed</h1><div class="string-uuid-change">N/A</div>',
        )  # not risky

        # Risky test coverage
        out = parse("[Describe test coverage new/current, TreeHerder]: none")
        self.assertEqual(
            out,
            '<h1 class="describe-test-coverage risky">Describe test coverage new/current, TreeHerder</h1><div class="describe-test-coverage risky">none</div>',
        )

        # Full comments
        for text_path in glob.glob("tests/uplift/*.txt"):
            with open(text_path, "r") as text:
                out = parse(text.read())
            html_path = text_path[:-4] + ".html"
            with open(html_path, "r") as html:
                self.assertEqual(out, html.read())

    def test_get_params_for_url(self):
        params = {"a": 1, "abc": 2, "efgh": 3, "bcd": [4, 5, 6]}
        self.assertEqual(
            utils.get_params_for_url(params), "?a=1&abc=2&bcd=4&bcd=5&bcd=6&efgh=3"
        )


if __name__ == "__main__":
    unittest.main()
