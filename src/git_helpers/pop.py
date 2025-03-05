import argparse
import logging
import re
import sys
from argparse import Namespace
from subprocess import PIPE
from subprocess import call
from subprocess import run

from git_helpers.util import UserError


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("stash", nargs="?")

    return parser.parse_args()


def main(stash: str | None) -> None:
    if stash is None:
        stash_args = []
    else:
        stash_args = [stash]

    result = run(["git", "stash", "apply", *stash_args], stdout=PIPE, text=True)

    if not result.returncode or re.search(
        r"^CONFLICT\b", result.stdout, flags=re.MULTILINE
    ):
        sys.exit(call(["git", "stash", "drop", *stash_args]))


def entry_point() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        main(**vars(parse_args()))
    except UserError as e:
        logging.error(f"error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.error("Operation interrupted.")
        sys.exit(130)
