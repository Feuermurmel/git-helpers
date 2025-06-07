import argparse
import sys
from argparse import Namespace
from subprocess import run

from git_helpers.git import get_branch_name
from git_helpers.git import get_commit_message
from git_helpers.git import has_staged_changes
from git_helpers.git import stage_all
from git_helpers.util import pass_parsed_args


def commit(message: str) -> None:
    args = ["--no-verify", "-m", message]

    if message == get_commit_message("HEAD"):
        args.append("--amend")

    run(["git", "commit", *args], stdout=sys.stderr.buffer)


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("subject_words", metavar="SUBJECT", nargs="*")

    return parser.parse_args()


@pass_parsed_args(parse_args)
def entry_point(subject_words: list[str]) -> None:
    if subject_words:
        subject = " ".join(subject_words)
    else:
        subject = get_branch_name("HEAD") or "HEAD"

    message = f"({subject})"

    if not has_staged_changes():
        stage_all()

    if has_staged_changes():
        commit(message)

    run(["git", "status"])
