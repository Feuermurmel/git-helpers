import argparse
import itertools
import re
import subprocess
import sys
from argparse import Namespace
from collections.abc import Iterator
from subprocess import check_output

from git_helpers.util import UserError
from git_helpers.util import get_commit_message
from git_helpers.util import git_rebase
from git_helpers.util import pass_parsed_args


def get_remote_refs() -> list[str]:
    def iter_refs() -> Iterator[str]:
        for i in check_output(["git", "show-ref"], text=True).splitlines():
            rev, ref = i.split(" ", 1)

            if re.match("refs/remotes/.*$", ref):
                yield rev

    return list(iter_refs())


def get_commits_not_reachable_by(base: str, other_commits: list[str]) -> list[str]:
    return check_output(
        ["git", "rev-list", "--no-merges", base, "--not", *other_commits], text=True
    ).splitlines()


def get_parent_commits(commit: str) -> list[str]:
    return check_output(
        ["git", "log", "-n", "1", "--pretty=%P", commit], text=True
    ).split()


def group_commits_by_message(commits: list[str]) -> list[list[tuple[str, str]]]:
    commits_with_messages = [(i, get_commit_message(i)) for i in commits]
    commit_order = {c: i for i, (c, _) in enumerate(commits_with_messages)}
    message_order = {m: i for i, (_, m) in enumerate(commits_with_messages)}

    def sort_key(x: tuple[str, str]) -> tuple[bool, int, int]:
        c, m = x

        return m.startswith("("), -message_order[m], -commit_order[c]

    def groupby_key(x: tuple[str, str]) -> str:
        c, m = x

        return m

    sorted_commits = sorted(commits_with_messages, key=sort_key)
    grouped_commits = itertools.groupby(sorted_commits, key=groupby_key)

    return [list(x) for _, x in grouped_commits]


def rebase(base: str | None, commits: list[str], dry_run: bool) -> None:
    def iter_todo_lines() -> Iterator[str]:
        for first, *rest in group_commits_by_message(commits):
            yield "p {} {}".format(*first)

            for i in rest:
                yield "f {} {}".format(*i)

    todo = "".join(i + "\n" for i in iter_todo_lines())

    if dry_run:
        print(todo)
    else:
        if base is None:
            base_arg = "--root"
        else:
            base_arg = base

        try:
            git_rebase(base_arg, todo)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_base", nargs="?")
    parser.add_argument("-n", "--dry-run", action="store_true")

    return parser.parse_args()


@pass_parsed_args(parse_args)
def entry_point(rebase_base: str | None, dry_run: bool) -> None:
    if rebase_base is None:
        other_commits = get_remote_refs()
    else:
        other_commits = [rebase_base]

    # Remove commit reachable by any of other_commits.
    rebased_commits = get_commits_not_reachable_by("HEAD", other_commits)

    if not rebased_commits:
        raise UserError("No commits left to rebase after removing the base commits.")

    parents = get_parent_commits(rebased_commits[-1])

    if not parents:
        base = None
    else:
        base = parents[0]

    rebase(base, rebased_commits, dry_run=dry_run)
