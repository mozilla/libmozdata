# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser


class Config(object):
    def get(section, option, default=None):
        raise NotImplementedError


class ConfigIni(Config):
    def __init__(self, path=None):
        self.config = ConfigParser()
        if path is not None:
            self.config.read(path)
        else:
            self.config.read(self.get_default_paths())
        self.path = path

    def get_default_paths(self):
        return [
            os.path.join(os.getcwd(), "mozdata.ini"),
            os.path.expanduser("~/.mozdata.ini"),
        ]

    def get(self, section, option, default=None, type=str):
        if not self.config.has_option(section, option):
            return default

        res = self.config.get(section, option)
        if type == list or type == set:
            return type([s.strip(" /t") for s in res.split(",")])
        else:
            return type(res)

    def __repr__(self):
        return self.path


class ConfigEnv(Config):
    def get(self, section, option, default=None):
        env = os.environ.get("LIBMOZDATA_CFG_" + section.upper() + "_" + option.upper())
        if not env:
            return default

        return env


__config = ConfigIni()


def set_config(conf):
    if not isinstance(conf, Config):
        raise TypeError("Argument must have type config.Config")
    global __config
    __config = conf


def get(section, option, default=None, type=str):
    global __config
    return __config.get(section, option, default=default, type=type)
