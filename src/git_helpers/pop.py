import argparse
import logging
import sys
from argparse import Namespace
from subprocess import call

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

    call(["git", "stash", "apply", *stash_args])
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
