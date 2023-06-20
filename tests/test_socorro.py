# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

from libmozdata import socorro


class SuperSearchTest(unittest.TestCase):
    def test_search(self):
        data = {}
        socorro.SuperSearch(
            params={
                "product": "Firefox",
                "signature": "~OOM",
                "_columns": ["uuid", "build_id"],
                "_results_number": 0,
                "_facets": ["product"],
            },
            handler=lambda j, d: d.update(j),
            handlerdata=data,
        ).wait()

        self.assertIsNotNone(data)


class ProcessedCrashTest(unittest.TestCase):
    def test_processed(self):
        uuid = []
        socorro.SuperSearch(
            params={
                "product": "Firefox",
                "signature": "~OOM",
                "_columns": ["uuid"],
                "_results_number": 2,
                "_facets": ["product"],
            },
            handler=lambda j, d: d.extend([j["hits"][0]["uuid"], j["hits"][1]["uuid"]]),
            handlerdata=uuid,
        ).wait()

        self.assertEqual(len(uuid), 2)
        processed = socorro.ProcessedCrash.get_processed(uuid)
        self.assertIsNotNone(processed)


class BugsTest(unittest.TestCase):
    def test_bugs(self):
        signature = []
        socorro.SuperSearch(
            params={
                "product": "Firefox",
                "signature": "~OOM",
                "_results_number": 0,
                "_facets": ["signature"],
            },
            handler=lambda j, d: d.extend(
                [
                    j["facets"]["signature"][0]["term"],
                    j["facets"]["signature"][1]["term"],
                ]
            ),
            handlerdata=signature,
        ).wait()

        self.assertEqual(len(signature), 2)
        bugs = socorro.Bugs.get_bugs(signature)
        self.assertIsNotNone(bugs)


class SignatureFirstDateTest(unittest.TestCase):
    def test_get_get_signatures(self):
        signature = [
            "TF_Notify",
            "EnterJit",
        ]
        signature_dates = socorro.SignatureFirstDate.get_signatures(signature)

        self.assertEqual(
            signature_dates,
            [
                {
                    "signature": "EnterJit",
                    "first_build": "20171014220542",
                    "first_date": "2017-10-15T13:24:10.225600+00:00",
                },
                {
                    "signature": "TF_Notify",
                    "first_build": "20100115144158",
                    "first_date": "2011-01-01T13:19:54.349341+00:00",
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
