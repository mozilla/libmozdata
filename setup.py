# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import

import os

from setuptools import find_packages, setup

here = os.path.dirname(__file__)


def load_requirements(filename):
    with open(os.path.join(here, filename)) as f:
        return f.read().strip().split("\n")


with open(os.path.join(here, "VERSION")) as f:
    version = f.read().strip()

setup(
    name="libmozdata",
    version=version,
    description="Library to access and aggregate several Mozilla data sources.",
    author="Mozilla Release Management",
    author_email="release-mgmt@mozilla.com",
    url="https://github.com/mozilla/libmozdata",
    install_requires=load_requirements("requirements.txt"),
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    include_package_data=True,
    zip_safe=False,
    license="MPL2",
    classifiers=[
        "Operating System :: OS Independent",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Programming Language :: Python :: 3",
    ],
)
