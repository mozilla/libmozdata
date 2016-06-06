# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from clouseau.connection import Query


class QueryTest(unittest.TestCase):

    def test(self):
        self.assertEqual(str(Query('https://www.mozilla.org/')), 'url: https://www.mozilla.org/')

    def test_args(self):
        representation = str(Query('https://www.mozilla.org/', {
            'var1': 'value1',
            'var2': ['value2', 'value3'],
        }))
        self.assertTrue(representation == 'url: https://www.mozilla.org/?var1=value1&var2=value2&var2=value3' or representation == 'url: https://www.mozilla.org/?var2=value2&var2=value3&var1=value1')
