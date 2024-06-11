import subprocess
import sys
from argparse import ArgumentParser
from argparse import Namespace

from git_helpers.util import UserError


def log(message: str):
    print(message, file=sys.stderr, flush=True)


def get_config(name: str, default: "str | None" = None) -> "str | None":
    result = subprocess.run(["git", "config", "--null", name], stdout=subprocess.PIPE)
    values = result.stdout.split(b"\x00")[:-1]

    assert values or result.returncode

    if values:
        return values[0].decode()
    else:
        return default


def get_stripped_output(command: "list[str]"):
    return subprocess.check_output(command).strip().decode()


def parse_args() -> Namespace:
    parser = ArgumentParser()

    parser.add_argument("remote_ref", nargs="?")

    return parser.parse_args()


def main(remote_ref: "str | None"):
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


def entry_point():
    try:
        main(**vars(parse_args()))
    except KeyboardInterrupt:
        log("Operation interrupted.")
        sys.exit(1)
    except UserError as e:
        log(f"error: {e}")
        sys.exit(2)
