# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import sys
import os
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser


class ConfigTest(unittest.TestCase):

    def tearDown(self):
        try:
            del sys.modules['libmozdata']
            del sys.modules['libmozdata.config']
        except KeyError:
            pass

        try:
            os.remove('config.ini')
        except:
            pass

        try:
            os.rename('config.ini.bak', 'config.ini')
        except:
            pass

    def setUp(self):
        try:
            os.rename('config.ini', 'config.ini.bak')
        except:
            pass

    def test_config_doesnt_exist(self):
        from libmozdata import config
        self.assertIsNone(config.get('Section', 'Option'))
        self.assertEqual(config.get('Section', 'Option', 'Default'), 'Default')

    def test_config_exists(self):
        with open('config.ini', 'w') as f:
            custom_conf = ConfigParser()
            custom_conf.add_section('Section')
            custom_conf.set('Section', 'Option', 'Value')
            custom_conf.set('Section', 'Option2', 'Value2')
            custom_conf.add_section('Section2')
            custom_conf.set('Section2', 'Option', 'Value3')
            custom_conf.write(f)

        from libmozdata import config

        self.assertEqual(config.get('Section', 'Option'), 'Value')
        self.assertEqual(config.get('Section', 'Option', 'Default'), 'Value')
        self.assertEqual(config.get('Section', 'Option2'), 'Value2')
        self.assertEqual(config.get('Section', 'Option2', 'Default'), 'Value2')
        self.assertEqual(config.get('Section2', 'Option'), 'Value3')
        self.assertEqual(config.get('Section2', 'Option', 'Default'), 'Value3')
        self.assertIsNone(config.get('Section', 'Option3'))
        self.assertEqual(config.get('Section', 'Option3', 'Default'), 'Default')


if __name__ == '__main__':
    unittest.main()
