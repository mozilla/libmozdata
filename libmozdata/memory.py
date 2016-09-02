# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import six
from . import utils


def isweird(addr, cpu_name):
    """Check if a memory address is weird

    Args:
        addr (str): a memory address
        cpu_name (str): cpu name

    Returns:
        bool: True if the address is weird
    """
    if not isinstance(addr, six.string_types):
        raise Exception('The memory address must be a string.')

    if addr == '0x0':
        return True

    addr = addr.lower()

    # Strip leading zeroes
    addr = addr[2:].lstrip('0')

    if utils.is64(cpu_name):
        if len(addr) <= 8:
            val = int(addr, 16)
            return val <= 0x10000  # first 64k
        elif addr.startswith('ffffffff'):
            addr = addr[8:]  # 8 == len('ffffffff')
            val = int(addr, 16)
            return val >= 0xffff0000  # last 64k
    else:
        val = int(addr, 16)
        return val <= 0x10000 or val >= 0xffff0000


def analyze(addrs, cpu_name=None):
    """

    """
    # we analyze the end of each address to find if a pattern exists
