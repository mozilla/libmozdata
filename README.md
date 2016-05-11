# clouseau
> Tool to find out some clues after crashes in using data from Socorro, Bugzilla and mercurial 

[![Build Status](https://api.travis-ci.org/calixteman/clouseau.svg?branch=master)](https://travis-ci.org/calixteman/clouseau)
[![codecov.io](https://img.shields.io/codecov/c/github/calixteman/clouseau/master.svg)](https://codecov.io/github/calixteman/clouseau?branch=master)

## Setup

Install the prerequisites via `pip`:
```sh
sudo pip install -r requirements.txt
```

## Running tests

Install test prerequisites via `pip`:
```sh
sudo pip install -r test-requirements.txt
```

Run tests:
```sh
coverage run --source=clouseau -m unittest discover tests/
```

## Credentials

For particular queries on Socorro or Bugzilla, it requires to have some API keys.

Create a file credentials.json (or an other name: it doesn't matter) with the following contents:
```
{
    "tokens":
    {
        "https://crash-stats.mozilla.com": "your Socorro API token",
        "https://bugzilla.mozilla.org": "your Bugzilla API token",
        "https://bugzilla-dev.allizom.org": "your Bugzilla-dev API token (for test only)",
        "https://sql.telemetry.mozilla.org": "your re:dash API token"
    }
}
```
