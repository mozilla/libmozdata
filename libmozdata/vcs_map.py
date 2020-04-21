import subprocess


def mercurial_to_git(repo_dir, mercurial_hash):
    p = subprocess.run(
        ["git", "cinnabar", "hg2git", mercurial_hash], cwd=repo_dir, capture_output=True
    )
    if p.returncode != 0:
        raise Exception(p.stderr)

    result = p.stdout.strip().decode("ascii")
    if result == "0000000000000000000000000000000000000000":
        raise Exception(f"Missing mapping for mercurial commit: {mercurial_hash}")

    return result


def git_to_mercurial(repo_dir, git_hash):
    p = subprocess.run(
        ["git", "cinnabar", "git2hg", git_hash], cwd=repo_dir, capture_output=True
    )
    if p.returncode != 0:
        raise Exception(p.stderr)

    result = p.stdout.strip().decode("ascii")
    if result == "0000000000000000000000000000000000000000":
        raise Exception(f"Missing mapping for git commit: {git_hash}")

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "repository_dir", help="Path to the Mercurial repository", action="store"
    )
    parser.add_argument(
        "git_repository_dir", help="Path to the git-cinnabar repository", action="store"
    )
    args = parser.parse_args()

    import hglib

    hg = hglib.open(args.repository_dir)
    cmd_args = hglib.util.cmdbuilder(b"log", template="{node}\n")
    x = hg.rawcommand(cmd_args)
    revs = x.splitlines()

    for rev in revs:
        git_to_mercurial(
            args.git_repository_dir,
            mercurial_to_git(args.git_repository_dir, rev.decode("ascii")),
        )
