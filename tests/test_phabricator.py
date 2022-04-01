import pickle
import unittest

from libmozdata import config
from libmozdata.phabricator import PhabricatorAPI, PhabricatorPatch


class PhabricatorTest(unittest.TestCase):
    def test_import(self):
        """
        Simply import the library to check that all requirements are available
        """
        from libmozdata.phabricator import PhabricatorAPI  # noqa

        assert True

    def test_pickle_phabricatorpatch(self):
        pickle.dumps(PhabricatorPatch("123", "PHID-DIFF-xxx", "", "rev", []))


class PhabricatorRequestTest(unittest.TestCase):
    def test_request_all_pages(self):
        token = config.get("Phabricator", "token", "")
        phab = PhabricatorAPI(token)

        constraints = {"createdStart": 1648600370, "createdEnd": 1648686770}
        data = phab.request_all_pages(
            "differential.revision.search", constraints=constraints
        )

        self.assertEqual(len(list(data)), 115)
