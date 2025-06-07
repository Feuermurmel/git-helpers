import argparse
import sys
from argparse import Namespace
from subprocess import PIPE
from subprocess import run

from git_helpers.util import get_commit_message
from git_helpers.util import pass_parsed_args


def get_branch_name(ref: str) -> str | None:
    result = run(["git", "symbolic-ref", "-q", "--short", ref], stdout=PIPE)

    if result.returncode:
        return None
    else:
        return result.stdout.decode().strip()


def has_staged_changes() -> bool:
    return run(["git", "diff", "--cached", "--quiet"]).returncode > 0


def stage_all() -> None:
    run(["git", "add", "--all", ":/"])


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
