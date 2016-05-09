# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import datetime
import json
from clouseau import utils

try:
    FileNotFoundError
except NameError:
    class FileNotFoundError(OSError):
        pass


class UtilsTest(unittest.TestCase):

    def test_get_best(self):
        self.assertEqual(utils.get_best(None), None)
        self.assertEqual(utils.get_best({'key1': 7, 'key2': 99, 'key3': 4}), 'key2')

    def test_get_timestamp(self):
        date = '1991-04-16'
        self.assertEqual(utils.get_timestamp(date), 671760000)
        self.assertEqual(utils.get_timestamp(datetime.datetime.strptime(date, '%Y-%m-%d')), 671760000)

    def test_get_date_ymd(self):
        pass

    def test_get_today(self):
        pass

    def test_get_date_str(self):
        pass

    def test_get_date(self):
        pass

    def test_get_now_timestamp(self):
        pass

    def test_is64(self):
        pass

    def test_percent(self):
        self.assertEqual(utils.percent(0.23), '23%')
        self.assertEqual(utils.percent(1), '100%')
        self.assertEqual(utils.percent(1.5), '150%')

    def test_simple_percent(self):
        self.assertEqual(utils.simple_percent(3), '3%')
        self.assertEqual(utils.simple_percent(3.0), '3%')
        self.assertEqual(utils.simple_percent(3.5), '3.5%')

    def test_get_credentials(self):
        with self.assertRaises(FileNotFoundError):
            utils.get_credentials('doesntexist')

        with open('/tmp/afile', 'w') as f:
            f.write('nothing')

        with self.assertRaises(json.decoder.JSONDecodeError):
            utils.get_credentials('/tmp/afile')

        with open('/tmp/afile', 'w') as f:
            json.dump({'key': 'value'}, f)

        self.assertEqual(utils.get_credentials('/tmp/afile'), {'key': 'value'})

    def test_get_sample(self):
        pass

    def test_get_date_from_buildid(self):
        self.assertEqual(utils.get_date_from_buildid('20160407164938'), datetime.datetime(2016, 4, 7, 0, 0))

if __name__ == '__main__':
    unittest.main()
