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

    def __init__(self, path=''):
        if not path:
            path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
        self.config = ConfigParser()
        self.config.read(path)

    def get(self, section, option, default=None):
        if not self.config.has_option(section, option):
            return default

        return self.config.get(section, option)


__config = ConfigIni()


def set_config(conf):
    if not isinstance(conf, Config):
        raise TypeError('Argument must have type config.Config')
    global __config
    __config = conf


def get(section, option, default=None):
    global __config
    return __config.get(section, option, default=default)
