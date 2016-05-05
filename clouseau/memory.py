# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import utils


def isweird(addr, cpu_name):
    """Check if a memory address is weird

    Args:
        addr (str): a memory address
        cpu_name (str): cpu name

    Returns:
        bool: True if the address is weird
    """
    if addr:
        addr = addr.lower()
        if addr == '0x0':
            return True
        if utils.is64(cpu_name):
            if len(addr) <= 10:
                val = int(addr, 16)
                if val <= (1 << 16):  # val <= 0xffff (ie: first 64k)
                    return True
            elif addr.startswith('0xffffffff'):
                addr = addr[10:]  # 10 == len('0xffffffff')
                val = int(addr, 16)
                if val >= ((1 << 32) - (1 << 16)):  # val >= 0xfffffffffff0000 (ie: last 64k)
                    return True
        else:
            val = int(addr, 16)
            if val <= 1 << 16:  # val <= 0xffff (ie: first 64k)
                return True
            if val >= ((1 << 32) - (1 << 16)):  # val >= 0xffff0000 (ie: last 64k)
                return True

    return False


def analyze(addrs, cpu_name=None):
    """

    """
    # we analyze the end of each address to find if a pattern exists
