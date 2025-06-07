import argparse
import re
import sys
from argparse import Namespace
from subprocess import PIPE
from subprocess import call
from subprocess import run

from git_helpers.util import pass_parsed_args


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("stash", nargs="?")

    return parser.parse_args()


@pass_parsed_args(parse_args)
def entry_point(stash: str | None) -> None:
    if stash is None:
        stash_args = []
    else:
        stash_args = [stash]

    result = run(["git", "stash", "apply", *stash_args], stdout=PIPE, text=True)

    if not result.returncode or re.search(
        r"^CONFLICT\b", result.stdout, flags=re.MULTILINE
    ):
        sys.exit(call(["git", "stash", "drop", *stash_args]))
