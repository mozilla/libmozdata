import unittest

import responses

from libmozdata import buildhub


class BuidlhubTest(unittest.TestCase):

    @responses.activate
    def test_get_distinct_versions(self):
        responses.add(
            responses.POST,
            buildhub.SEARCH_URL,
            json={
                "aggregations": {
                    "myaggs": {
                        "target.version": {
                            "buckets": [{"key": "64.2"}, {"key": "65.1"}]
                        }
                    }
                }
            },
        )
        versions = buildhub.get_distinct_versions()
        self.assertEqual(versions, ["65.1", "64.2"])

    @responses.activate
    def test_get_distinct_versions_majors(self):
        responses.add(
            responses.POST,
            buildhub.SEARCH_URL,
            json={
                "aggregations": {
                    "myaggs": {"target.version": {"buckets": [{"key": "65.1"}]}}
                }
            },
        )
        versions = buildhub.get_distinct_versions(major="65")
        self.assertEqual(versions, ["65.1"])

    @responses.activate
    def test_get_distinct_buildids(self):
        responses.add(
            responses.POST,
            buildhub.SEARCH_URL,
            json={
                "aggregations": {
                    "myaggs": {
                        "build.id": {
                            "buckets": [
                                {"key": "20181130102244"},
                                {"key": "20181029104433"},
                                {"key": "20181029104433"},
                            ]
                        }
                    }
                }
            },
        )
        versions = buildhub.get_distinct_buildids()
        self.assertEqual(versions, ["20181130102244", "20181029104433"])

    @responses.activate
    def test_get_distinct_buildids_startswith(self):
        responses.add(
            responses.POST,
            buildhub.SEARCH_URL,
            json={
                "aggregations": {
                    "myaggs": {"build.id": {"buckets": [{"key": "20181130102244"}]}}
                }
            },
        )
        versions = buildhub.get_distinct_buildids(startswith="201811")
        self.assertEqual(versions, ["20181130102244"])
