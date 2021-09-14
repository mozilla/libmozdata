# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import requests


class LandoWarnings(object):
    """
    Encapsulates lando warning calls
    """

    def __init__(self, api_url, api_key):
        self.api_url = f"{api_url}/diff_warnings"
        self.api_key = api_key

    def del_warnings(self, warnings):
        """
        Deletes warnings from Lando based on a json warnings list
        """
        for warning in warnings:
            warning_id = warning["id"]

            response = requests.delete(
                f"{self.api_url}/{warning_id}",
                headers={"X-Phabricator-API-Key": self.api_key},
            )

            if response.status_code != 200:
                raise Exception(f"Failed to delete warning with ID {warning_id}!")

    def add_warning(self, warning, revision_id, diff_id):
        """
        Adds a warning to Lando
        """
        response = requests.post(
            self.api_url,
            json={
                "revision_id": revision_id,
                "diff_id": diff_id,
                "group": "LINT",
                "data": {"message": warning},
            },
            headers={"X-Phabricator-API-Key": self.api_key},
        )
        if response.status_code != 201:
            raise Exception(
                f"Failed to add warnings for revision_id {revision_id} and diff_id {diff_id}!"
            )

    def get_warnings(self, revision_id, diff_id):
        """
        Gets a list of warnings
        """
        response = requests.get(
            self.api_url,
            params={
                "revision_id": revision_id,
                "diff_id": diff_id,
                "group": "LINT",
            },
            headers={"X-Phabricator-API-Key": self.api_key},
        )
        if response.status_code != 200:
            raise Exception(
                f"Failed to get warnings for revision_id {revision_id} and diff_id {diff_id}!"
            )

        return response.json()

    def del_all_warnings(self, revision_id, diff_id):
        """
        Deletes all warnings
        """
        current_warnings = self.get_warnings(revision_id, diff_id)

        if len(current_warnings):
            return self.del_warnings(current_warnings)
