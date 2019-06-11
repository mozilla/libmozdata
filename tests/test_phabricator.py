import unittest


class PhabricatorTest(unittest.TestCase):
    def test_import(self):
        """
        Simply import the library to check that all requirements are available
        """
        from libmozdata.phabricator import PhabricatorAPI  # noqa

        assert True
