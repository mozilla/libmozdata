# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

__config = None


def __read_config():
    global __config
    __config = ConfigParser()
    __config.read(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini'))


def get(section, option, default=None):
    if __config is None:
        __read_config()

    if not __config.has_option(section, option):
        return default

    return __config.get(section, option)
