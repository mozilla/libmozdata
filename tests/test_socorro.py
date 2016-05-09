# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from clouseau import socorro


class SuperSearchTest(unittest.TestCase):

    def test_search(self):
        data = {}
        socorro.SuperSearch(params={'product': 'Firefox',
                                    'signature': '~OOM',
                                    '_columns': ['uuid', 'build_id'],
                                    '_results_number': 0,
                                    '_facets': ['product']},
                            handler=lambda j, d: d.update(j),
                            handlerdata=data).wait()

        self.assertIsNot(data, None)


class ProcessedCrashTest(unittest.TestCase):

    def test_processed(self):
        uuid = []
        socorro.SuperSearch(params={'product': 'Firefox',
                                    'signature': '~OOM',
                                    '_columns': ['uuid'],
                                    '_results_number': 2,
                                    '_facets': ['product']},
                            handler=lambda j, d: d.extend([j['hits'][0]['uuid'], j['hits'][1]['uuid']]),
                            handlerdata=uuid).wait()

        self.assertEqual(len(uuid), 2)
        processed = socorro.ProcessedCrash.get_processed(uuid)
        self.assertIsNot(processed, None)


class PlatformsTest(unittest.TestCase):

    def test_platforms(self):
        platforms = socorro.Platforms.get_all()
        self.assertIsNot(platforms, None)

    def test_cached_platforms(self):
        platforms = socorro.Platforms.get_cached_all()
        self.assertIsNot(platforms, None)


class ProductVersionsTest(unittest.TestCase):

    def test_versions(self):
        versions = socorro.ProductVersions.get_active()
        self.assertIsNot(versions, None)

    def test_cached_versions(self):
        cached_versions = socorro.ProductVersions.get_cached_versions()
        self.assertIsNot(cached_versions, None)


class TCBSTest(unittest.TestCase):

    def test_tcbs(self):
        tc = socorro.TCBS.get_firefox_topcrashes(channel='nightly', limit=1)
        self.assertIsNot(tc, None)


class SignatureTrendTest(unittest.TestCase):

    def test_signature(self):
        signature = []
        socorro.SuperSearch(params={'product': 'Firefox',
                                    'signature': '~OOM',
                                    '_results_number': 0,
                                    '_facets': ['signature']},
                            handler=lambda j, d: d.extend([j['facets']['signature'][0]['term'], j['facets']['signature'][1]['term']]),
                            handlerdata=signature).wait()

        self.assertEqual(len(signature), 2)
        trend = socorro.SignatureTrend.get_trend(signature, channel='nightly')
        self.assertIsNot(trend, None)


class ADITest(unittest.TestCase):

    def test_adi(self):
        adis = socorro.ADI.get(channel='nightly')
        self.assertIsNot(adis, None)


class SignatureURLsTest(unittest.TestCase):

    def test_signature(self):
        signature = []
        socorro.SuperSearch(params={'product': 'Firefox',
                                    'signature': '~OOM',
                                    '_results_number': 0,
                                    '_facets': ['signature']},
                            handler=lambda j, d: d.extend([j['facets']['signature'][0]['term'], j['facets']['signature'][1]['term']]),
                            handlerdata=signature).wait()

        self.assertEqual(len(signature), 2)
        urls = socorro.SignatureURLs.get_urls(signature, channel='nightly')
        self.assertIsNot(urls, None)


class BugsTest(unittest.TestCase):

    def test_bugs(self):
        signature = []
        socorro.SuperSearch(params={'product': 'Firefox',
                                    'signature': '~OOM',
                                    '_results_number': 0,
                                    '_facets': ['signature']},
                            handler=lambda j, d: d.extend([j['facets']['signature'][0]['term'], j['facets']['signature'][1]['term']]),
                            handlerdata=signature).wait()

        self.assertEqual(len(signature), 2)
        bugs = socorro.Bugs.get_bugs(signature)
        self.assertIsNot(bugs, None)


if __name__ == '__main__':
    unittest.main()
