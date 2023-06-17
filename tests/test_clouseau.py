# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import responses

from libmozdata import clouseau
from tests.auto_mock import MockTestCase


class ReportsTest(MockTestCase):
    mock_urls = [clouseau.Reports.URL]

    @responses.activate
    def test_reports(self):
        signatures = {
            "mozilla::dom::Link::LinkState",
            "UIItemsView::_OnBatchTimer",
        }

        res = clouseau.Reports.get_by_signatures(signatures)

        self.assertEqual(res.keys(), signatures)
