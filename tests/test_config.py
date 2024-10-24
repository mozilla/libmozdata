# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import unittest

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser


class ConfigTest(unittest.TestCase):
    def tearDown(self):
        try:
            del sys.modules["libmozdata"]
            del sys.modules["libmozdata.config"]
        except KeyError:
            pass

        try:
            os.remove("config.ini")
        except OSError:
            pass

        try:
            os.remove("mozdata.ini")
        except OSError:
            pass

        try:
            os.remove(os.path.expanduser("~/.mozdata.ini"))
        except OSError:
            pass

        try:
            os.rename("mozdata.ini.bak", "mozdata.ini")
        except OSError:
            pass

        try:
            os.rename(
                os.path.expanduser("~/.mozdata.ini.bak"),
                os.path.expanduser("~/.mozdata.ini"),
            )
        except OSError:
            pass

    def setUp(self):
        try:
            os.rename("mozdata.ini", "mozdata.ini.bak")
        except OSError:
            pass

        try:
            os.rename(
                os.path.expanduser("~/.mozdata.ini"),
                os.path.expanduser("~/.mozdata.ini.bak"),
            )
        except OSError:
            pass

    def test_config_doesnt_exist(self):
        from libmozdata import config

        self.assertIsNone(config.get("Section", "Option"))
        self.assertEqual(config.get("Section", "Option", "Default"), "Default")

    def test_config_exists_in_cwd(self):
        with open("mozdata.ini", "w") as f:
            custom_conf = ConfigParser()
            custom_conf.add_section("Section")
            custom_conf.set("Section", "Option", "Value")
            custom_conf.set("Section", "Option2", "Value2")
            custom_conf.add_section("Section2")
            custom_conf.set("Section2", "Option", "Value3")
            custom_conf.write(f)

        from libmozdata import config

        self.assertEqual(config.get("Section", "Option"), "Value")
        self.assertEqual(config.get("Section", "Option", "Default"), "Value")
        self.assertEqual(config.get("Section", "Option2"), "Value2")
        self.assertEqual(config.get("Section", "Option2", "Default"), "Value2")
        self.assertEqual(config.get("Section2", "Option"), "Value3")
        self.assertEqual(config.get("Section2", "Option", "Default"), "Value3")
        self.assertIsNone(config.get("Section", "Option3"))
        self.assertEqual(config.get("Section", "Option3", "Default"), "Default")

    def test_config_get_with_type(self):
        with open("mozdata.ini", "w") as f:
            custom_conf = ConfigParser()
            custom_conf.add_section("Section")
            custom_conf.set("Section", "Option", "Value")
            custom_conf.set("Section", "Option2", "123")
            custom_conf.add_section("Section2")
            custom_conf.set("Section2", "Option", "Value1, Value2, Value3")
            custom_conf.write(f)

        from libmozdata import config

        self.assertEqual(config.get("Section", "Option"), "Value")
        self.assertEqual(config.get("Section", "Option2", type=int), 123)
        self.assertEqual(config.get("Section", "Option2", type=str), "123")
        self.assertEqual(
            config.get("Section2", "Option", type=list), ["Value1", "Value2", "Value3"]
        )
        self.assertEqual(
            config.get("Section2", "Option", type=set), {"Value1", "Value2", "Value3"}
        )

    def test_config_exists_in_home(self):
        with open(os.path.expanduser("~/.mozdata.ini"), "w") as f:
            custom_conf = ConfigParser()
            custom_conf.add_section("Section3")
            custom_conf.set("Section3", "Option5", "Value8")
            custom_conf.set("Section3", "Option6", "Value9")
            custom_conf.add_section("Section4")
            custom_conf.set("Section4", "Option7", "Value10")
            custom_conf.write(f)

        from libmozdata import config

        self.assertEqual(config.get("Section3", "Option5"), "Value8")
        self.assertEqual(config.get("Section3", "Option5", "Default"), "Value8")
        self.assertEqual(config.get("Section3", "Option6"), "Value9")
        self.assertEqual(config.get("Section3", "Option6", "Default"), "Value9")
        self.assertEqual(config.get("Section4", "Option7"), "Value10")
        self.assertEqual(config.get("Section4", "Option7", "Default"), "Value10")
        self.assertIsNone(config.get("Section3", "Option7"))
        self.assertEqual(config.get("Section3", "Option7", "Default"), "Default")

    def test_config_exists_in_custom_path(self):
        with open("config.ini", "w") as f:
            custom_conf = ConfigParser()
            custom_conf.add_section("Section5")
            custom_conf.set("Section5", "Option7", "Value11")
            custom_conf.set("Section5", "Option8", "Value12")
            custom_conf.add_section("Section6")
            custom_conf.set("Section6", "Option9", "Value13")
            custom_conf.write(f)

        from libmozdata import config

        config.set_config(config.ConfigIni("config.ini"))

        self.assertEqual(config.get("Section5", "Option7"), "Value11")
        self.assertEqual(config.get("Section5", "Option7", "Default"), "Value11")
        self.assertEqual(config.get("Section5", "Option8"), "Value12")
        self.assertEqual(config.get("Section5", "Option8", "Default"), "Value12")
        self.assertEqual(config.get("Section6", "Option9"), "Value13")
        self.assertEqual(config.get("Section6", "Option9", "Default"), "Value13")
        self.assertIsNone(config.get("Section5", "Option9"))
        self.assertEqual(config.get("Section5", "Option9", "Default"), "Default")

    def test_get_required(self):
        with open("config.ini", "w") as f:
            custom_conf = ConfigParser()
            custom_conf.add_section("User-Agent")
            custom_conf.set("User-Agent", "something", "value")
            custom_conf.write(f)

        from libmozdata import config

        config.set_config(config.ConfigIni("config.ini"))

        with self.assertRaisesRegex(
            AssertionError, "Option name in section User-Agent is not set"
        ):
            config.get("User-Agent", "name", required=True)

    def test_set_default_value(self):
        """
        The set_value function correctly sets a value in the configuration
        """
        with open("config.ini", "w") as f:
            custom_conf = ConfigParser()
            custom_conf.add_section("Section 1")
            custom_conf.set("Section 1", "something", "value")
            custom_conf.write(f)

        from libmozdata import config

        config.set_config(config.ConfigIni("config.ini"))
        config.set_default_value("User-Agent", "name", "something-0.1.1")

        self.assertEqual(config.get("User-Agent", "name"), "something-0.1.1")

    def test_local_config_fallback(self):
        with open("config.ini", "w") as f:
            custom_conf = ConfigParser()
            custom_conf.add_section("Section 1")
            custom_conf.set("Section 1", "something", "value")
            custom_conf.write(f)

        from libmozdata import config

        config.set_config(config.ConfigIni("config.ini"))
        config.set_default_value("User-Agent", "name", "something-0.1.1")

        self.assertEqual(
            config.get("User-Agent", "name", required=True), "something-0.1.1"
        )


class ConfigEnvTest(unittest.TestCase):
    def test_config_env(self):
        from libmozdata import config

        os.environ["LIBMOZDATA_CFG_BUGZILLA_TOKEN"] = "my_bugzilla_api_key"
        cfg = config.ConfigEnv()
        self.assertEqual(cfg.get("Bugzilla", "token", "default"), "my_bugzilla_api_key")
        self.assertEqual(cfg.get("Section", "Option", "default"), "default")


if __name__ == "__main__":
    unittest.main()
