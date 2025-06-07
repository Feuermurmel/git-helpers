import argparse
from argparse import Namespace
from subprocess import CalledProcessError

from git_helpers.rebasing import edit_commit
from git_helpers.util import pass_parsed_args


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("commit")

    return parser.parse_args()


@pass_parsed_args(parse_args)
def entry_point(commit: str) -> None:
    try:
        edit_commit(commit)
    except CalledProcessError as e:
        # An error message should have been printed.
        pass
