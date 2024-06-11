import argparse
import logging
import subprocess
import sys
from argparse import Namespace
from subprocess import PIPE
from typing import IO
from typing import Any

from git_helpers.util import UserError


class CommandResult:
    def __init__(self, code: int, out: bytes, err: bytes):
        self.code = code
        self.out = out
        self.err = err


def command(
    *args: str,
    use_stdout: bool = False,
    use_stderr: bool = False,
    stdout_on_stderr: bool = False,
    allow_error: bool = False,
    cwd: str | None = None,
) -> CommandResult:
    if use_stdout:
        assert not stdout_on_stderr

        stdout: int | IO[Any] = PIPE
    elif stdout_on_stderr:
        stdout = sys.stderr.buffer
    else:
        stdout = sys.stdout

    if use_stderr:
        stderr: int | IO[Any] = PIPE
    else:
        stderr = sys.stderr

    process = subprocess.Popen(args, stdout=stdout, stderr=stderr, cwd=cwd)
    out, err = process.communicate()
    res = CommandResult(process.returncode, out, out)

    if not allow_error:
        assert not res.code

    return res


def get_branch_name(ref: str) -> str | None:
    res = command(
        "git", "symbolic-ref", "-q", "--short", ref, allow_error=True, use_stdout=True
    )

    if res.code:
        return None
    else:
        return res.out.decode().strip()


def has_staged_changes() -> bool:
    return command("git", "diff", "--cached", "--quiet", allow_error=True).code > 0


def stage_all() -> None:
    command("git", "add", "--all", ":/")


def commit(message: str) -> None:
    command("git", "commit", "--no-verify", "-m", message, stdout_on_stderr=True)


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("branch_name", nargs="?")

    return parser.parse_args()


def main(branch_name: str | None) -> None:
    if branch_name is None:
        branch_name = get_branch_name("HEAD")

        if branch_name is None:
            branch_name = "HEAD"

    if not has_staged_changes():
        stage_all()

    if has_staged_changes():
        commit(f"({branch_name})")

    command("git", "status")


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
