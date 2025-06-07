import argparse
import itertools
import subprocess
import sys
from argparse import Namespace

from git_helpers.git import get_commit_message
from git_helpers.git import get_commits_not_reachable_by
from git_helpers.git import get_parent_commits
from git_helpers.git import get_remote_refs
from git_helpers.rebasing import RebaseTodo
from git_helpers.rebasing import git_rebase
from git_helpers.util import UserError
from git_helpers.util import pass_parsed_args


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


def create_todo(commits: list[str]) -> RebaseTodo:
    todo_lines = []

    for grouped_commits in group_commits_by_message(commits):
        for i, (commit, message) in enumerate(grouped_commits):
            command = "pick" if i == 0 else "fixup"
            todo_lines.append(f"{command} {commit} {message}")

    return RebaseTodo("".join(f"{i}\n" for i in todo_lines))


def rebase(commits: list[str], dry_run: bool) -> None:
    todo = create_todo(commits)

    if dry_run:
        print(todo)
    else:
        parents = get_parent_commits(commits[-1])

        if parents:
            base_arg = parents[0]
        else:
            base_arg = "--root"

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

    rebase(rebased_commits, dry_run=dry_run)
