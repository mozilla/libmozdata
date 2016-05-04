# clouseau
> Tool to find out some clues after crashes in using data from Socorro, Bugzilla and mercurial 

[![Build Status](https://api.travis-ci.org/calixte/clouseau.svg?branch=master)](https://travis-ci.org/calixte/clouseau)
[![codecov.io](https://img.shields.io/codecov/c/github/calixte/clouseau/master.svg)](https://codecov.io/github/calixte/clouseau?branch=master)

## Running tests

Install test prerequisites via `pip`:
```sh
pip install -r test-requirements.txt
```

Run tests:
```sh
coverage run --source=clouseau -m unittest discover tests/
```
