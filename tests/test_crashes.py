# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import os
from clouseau.stability import crashes


class CrashesTest(unittest.TestCase):

    def test_crashes(self):
        credentials = {
            'tokens': {
                'https://sql.telemetry.mozilla.org': os.environ.get('API_KEY_346', ''),
            }
        }

        stats = crashes.get('release', 'yesterday', versions=46, duration=11, tcbs_limit=50, credentials=credentials)

        self.assertIn('start_date', stats)
        self.assertIn('end_date', stats)
        self.assertIn('versions', stats)
        self.assertIn('adi', stats)
        self.assertIn('khours', stats)
        self.assertIn('throttle', stats)
        for sign in stats['signatures'].values():
            self.assertIn('bugs', sign)
            self.assertIn('startup_percent', sign)
            self.assertIn('startup_crash', sign)
            self.assertIn('tc_rank', sign)
            self.assertIn('crash_count', sign)
            self.assertIn('crash_by_day', sign)
            self.assertIn('crash_stats_per_mega_adi', sign)
            self.assertIn('crash_stats_per_mega_hours', sign)


if __name__ == '__main__':
    unittest.main()
