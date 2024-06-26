import logging
import subprocess
import sys
from argparse import ArgumentParser
from argparse import Namespace

from git_helpers.util import UserError
from git_helpers.util import get_config
from git_helpers.util import get_stripped_output


def parse_args() -> Namespace:
    parser = ArgumentParser()

    parser.add_argument("remote_ref", nargs="?")

    return parser.parse_args()


def main(remote_ref: str | None) -> None:
    remote = get_config("upush.remote", "origin")
    branch = get_stripped_output(["git", "branch", "--show-current"])

    if remote_ref is None:
        prefix = get_config("upush.prefix", "")
        remote_ref = prefix + branch

    if not branch:
        raise UserError("You are not currently on a branch.")

    branch_remote = get_config(f"branch.{branch}.remote")

    if branch_remote is not None:
        raise UserError(f"Branch already setup up to push to remote {branch_remote}.")

    try:
        subprocess.check_call(
            ["git", "push", "--set-upstream", f"{remote}", f"{branch}:{remote_ref}"]
        )
    except subprocess.CalledProcessError as e:
        raise UserError(f"{e}")


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
