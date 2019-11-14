import argparse
import io
import os
import shutil
import tarfile

import requests

MAP_FILE_URL = "https://moz-vcssync.s3-us-west-2.amazonaws.com/mapping/gecko-dev/git-mapfile.tar.bz2"
VCS_MAP_PATH = "gecko-dev_git-mapfile"

git_to_mercurial_mapping = {}
mercurial_to_git_mapping = {}

MAPFILE_LOADED = False


def download_mapfile():
    global MAPFILE_LOADED

    r = requests.head(MAP_FILE_URL, allow_redirects=True)

    new_etag = r.headers["ETag"]

    try:
        with open(f"{VCS_MAP_PATH}.etag", "r") as f:
            old_etag = f.read()
    except IOError:
        old_etag = None

    if old_etag == new_etag and os.path.exists(VCS_MAP_PATH):
        return False

    r = requests.get(MAP_FILE_URL)

    with tarfile.open(fileobj=io.BytesIO(r.content), mode="r:bz2") as tar:
        with open(VCS_MAP_PATH, "wb") as f:
            shutil.copyfileobj(
                tar.extractfile("./build/conversion/beagle/.hg/git-mapfile"), f
            )

    with open(f"{VCS_MAP_PATH}.etag", "w") as f:
        f.write(new_etag)

    MAPFILE_LOADED = False
    return True


def load_mapfile():
    global MAPFILE_LOADED
    if MAPFILE_LOADED:
        return

    MAPFILE_LOADED = True

    def _read_mapping_file(path):
        with open(path, "r") as f:
            for line in f:
                git_hash, mercurial_hash = line.rstrip("\n").split(" ")
                git_to_mercurial_mapping[git_hash] = mercurial_hash
                mercurial_to_git_mapping[mercurial_hash] = git_hash

    try:
        _read_mapping_file(VCS_MAP_PATH)
    except FileNotFoundError:
        pass


def mercurial_to_git(mercurial_hash):
    load_mapfile()

    if mercurial_hash not in mercurial_to_git_mapping:
        if download_mapfile():
            load_mapfile()

    if mercurial_hash not in mercurial_to_git_mapping:
        raise Exception(f"Missing mercurial commit in the VCS map: {mercurial_hash}")

    return mercurial_to_git_mapping[mercurial_hash]


def git_to_mercurial(git_hash):
    load_mapfile()

    if git_hash not in git_to_mercurial_mapping:
        if download_mapfile():
            load_mapfile()

    if git_hash not in git_to_mercurial_mapping:
        raise Exception(f"Missing git commit in the VCS map: {git_hash}")

    return git_to_mercurial_mapping[git_hash]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repository_dir", help="Path to the repository", action="store")
    args = parser.parse_args()

    download_mapfile()

    import hglib

    hg = hglib.open(args.repository_dir)
    args = hglib.util.cmdbuilder(b"log", template="{node}\n")
    x = hg.rawcommand(args)
    revs = x.splitlines()

    for rev in revs:
        mercurial_to_git(rev.decode("ascii"))
