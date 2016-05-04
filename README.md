# clouseau
> Tool to find out some clues after crashes in using data from Socorro, Bugzilla and mercurial 

## Running tests

Install test prerequisites via `pip`:
```sh
pip install -r test-requirements.txt
```

Run tests:
```sh
coverage run --source=clouseau -m unittest discover tests/
```
