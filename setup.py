# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import

import os

from setuptools import find_packages, setup


here = os.path.dirname(__file__)

with open(os.path.join(here, 'VERSION')) as f:
    version = f.read().strip()

with open(os.path.join(here, 'requirements.txt')) as f:
    install_requires = f.read().strip().split('\n')

setup(
    name='libmozdata',
    version=version,
    description='Library to access and aggregate several Mozilla data sources.',
    author='Mozilla Release Management',
    author_email='release-mgmt@mozilla.com',
    url='https://github.com/mozilla/libmozdata',
    install_requires=install_requires,
    packages=find_packages(exclude=['*.tests', '*.tests.*', 'tests.*', 'tests']),
    include_package_data=True,
    zip_safe=False,
    license='MPL2',
)
