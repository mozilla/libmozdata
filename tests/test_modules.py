# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from clouseau import modules


class ModulesTest(unittest.TestCase):

    def test_module_from_path(self):
        mm = modules.MozillaModules()
        self.assertEqual(mm.module_from_path('xpcom/threads/nsEnvironment.cpp')['name'], 'XPCOM')
        self.assertEqual(mm.module_from_path('xpcom/strinFile')['name'], 'XPCOM')
        self.assertEqual(mm.module_from_path('xpcom/tests/component/TestComponent.cpp')['name'], 'XPCOM')
        self.assertEqual(mm.module_from_path('xpcom/base/nsCycleCollector.h')['name'], 'Cycle Collector')
        self.assertEqual(mm.module_from_path('xpcom/string/nsString.cpp')['name'], 'String')
        self.assertEqual(mm.module_from_path('xpcom/string/')['name'], 'String')
        self.assertEqual(mm.module_from_path('xpcom/string')['name'], 'String')
        self.assertEqual(mm.module_from_path('tools/cvs2hg-import.py')['name'], 'Build Config')
        self.assertEqual(mm.module_from_path('doesntexist'), None)

        # Test heuristics
        self.assertEqual(mm.module_from_path('old-configure.in')['name'], 'Build Config')
        self.assertEqual(mm.module_from_path('python/mach/mach/dispatcher.py')['name'], 'Build Config')

        self.assertEqual(mm.module_from_path('js/public/GCPolicyAPI.h')['name'], 'JavaScript')

        self.assertEqual(mm.module_from_path('security/certverifier/CertVerifier.cpp')['name'], 'security')
        self.assertEqual(mm.module_from_path('security/pkix/lib/pkixnames.cpp')['name'], 'security')
        self.assertEqual(mm.module_from_path('security/manager/')['name'], 'Security - Mozilla PSM Glue')

        self.assertEqual(mm.module_from_path('tools/profiler/core/platform.h')['name'], 'Code Analysis and Debugging Tools')
        self.assertEqual(mm.module_from_path('tools/update-packaging/')['name'], 'Build and Release Tools')

    def test_module_info(self):
        mm = modules.MozillaModules()
        self.assertEqual(mm.module_info('XPCOM')['name'], 'XPCOM')
        self.assertEqual(mm.module_info('xpcom')['name'], 'XPCOM')
        self.assertEqual(mm.module_info('DoesntExist'), None)

if __name__ == '__main__':
    unittest.main()
