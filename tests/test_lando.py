import unittest

import responses

from libmozdata.lando import LandoWarnings

MOCK_LANDO_API_URL = "http://api.lando.test"
MOCK_LANDO_TOKEN = "Some Test Token"

MOCK_DIFF_ID = 0
MOCK_REV_ID = 0
MOCK_GROUP = "LINT"

MOCK_WARNINGS_ID = 100

MOCK_WARNING_MESSAGE = "There are still warnings"

MOCK_WARNINGS_DATA = [
    {
        "data": MOCK_WARNING_MESSAGE,
        "diff_id": MOCK_DIFF_ID,
        "revision_id": MOCK_REV_ID,
        "group": MOCK_GROUP,
        "id": MOCK_WARNINGS_ID,
    }
]

MOCK_WARNINGS_DATA_PUT = {
    "revision_id": MOCK_REV_ID,
    "diff_id": MOCK_DIFF_ID,
    "group": MOCK_GROUP,
    "data": {"message": MOCK_WARNING_MESSAGE},
}


class Test_LandoWarnings(unittest.TestCase):
    @responses.activate
    def test_get_warnings(self):
        responses.add(
            responses.GET,
            f"{MOCK_LANDO_API_URL}/diff_warnings/?revision_id={MOCK_REV_ID}&diff_id={MOCK_DIFF_ID}&group={MOCK_GROUP}",
            json=MOCK_WARNINGS_DATA,
            headers={"X-Phabricator-API-Key": MOCK_LANDO_TOKEN},
            status=200,
        )

        mock_lando = LandoWarnings(MOCK_LANDO_API_URL, MOCK_LANDO_TOKEN)

        self.assertEqual(
            mock_lando.get_warnings(MOCK_REV_ID, MOCK_DIFF_ID), MOCK_WARNINGS_DATA
        )
        self.assertEqual(
            responses.calls[0].request.headers["X-Phabricator-API-Key"],
            MOCK_LANDO_TOKEN,
        )

    @responses.activate
    def test_get_warnings_fail(self):
        # Error code with 404
        responses.add(
            responses.GET,
            f"{MOCK_LANDO_API_URL}/diff_warnings/?revision_id={MOCK_REV_ID}&diff_id={MOCK_DIFF_ID}&group={MOCK_GROUP}",
            body="Nice error",
            headers={"X-Phabricator-API-Key": MOCK_LANDO_TOKEN},
            status=400,
        )
        mock_lando = LandoWarnings(MOCK_LANDO_API_URL, MOCK_LANDO_TOKEN)

        try:
            mock_lando.get_warnings(MOCK_REV_ID, MOCK_DIFF_ID)
        except Exception as ex:
            self.assertEqual(
                str(ex),
                "Failed to get warnings for revision_id 0 and diff_id 0 with error 400:\nNice error",
            )

    @responses.activate
    def test_add_warnings(self):
        responses.add(
            responses.POST,
            f"{MOCK_LANDO_API_URL}/diff_warnings/",
            match=[responses.json_params_matcher(MOCK_WARNINGS_DATA_PUT)],
            headers={"X-Phabricator-API-Key": MOCK_LANDO_TOKEN},
            status=201,
        )

        mock_lando = LandoWarnings(MOCK_LANDO_API_URL, MOCK_LANDO_TOKEN)

        self.assertEqual(
            mock_lando.add_warning(MOCK_WARNING_MESSAGE, MOCK_REV_ID, MOCK_DIFF_ID),
            None,
        )

        self.assertEqual(
            responses.calls[0].request.headers["X-Phabricator-API-Key"],
            MOCK_LANDO_TOKEN,
        )

    @responses.activate
    def test_del_all_warnings(self):
        responses.add(
            responses.GET,
            f"{MOCK_LANDO_API_URL}/diff_warnings/?revision_id={MOCK_REV_ID}&diff_id={MOCK_DIFF_ID}&group={MOCK_GROUP}",
            json=MOCK_WARNINGS_DATA,
            headers={"X-Phabricator-API-Key": MOCK_LANDO_TOKEN},
            status=200,
        )
        responses.add(
            responses.DELETE,
            f"{MOCK_LANDO_API_URL}/diff_warnings/{MOCK_WARNINGS_ID}",
            headers={"X-Phabricator-API-Key": MOCK_LANDO_TOKEN},
            status=200,
        )
        mock_lando = LandoWarnings(MOCK_LANDO_API_URL, MOCK_LANDO_TOKEN)

        self.assertEqual(mock_lando.del_all_warnings(MOCK_REV_ID, MOCK_DIFF_ID), None)
        self.assertEqual(
            responses.calls[0].request.headers["X-Phabricator-API-Key"],
            MOCK_LANDO_TOKEN,
        )

    @responses.activate
    def test_del_warnings_fail(self):
        MOCK_WARNINGS_DATA = [{"id": MOCK_WARNINGS_ID}]
        responses.add(
            responses.DELETE,
            f"{MOCK_LANDO_API_URL}/diff_warnings/{MOCK_WARNINGS_ID}",
            body="Delete error",
            headers={"X-Phabricator-API-Key": MOCK_LANDO_TOKEN},
            status=400,
        )

        mock_lando = LandoWarnings(MOCK_LANDO_API_URL, MOCK_LANDO_TOKEN)

        try:
            mock_lando.del_warnings(MOCK_WARNINGS_DATA)
        except Exception as ex:
            self.assertEqual(
                str(ex),
                f"Failed to delete warning with ID {MOCK_WARNINGS_ID} with error 400:\nDelete error",
            )


if __name__ == "__main__":
    unittest.main()
