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


def get_current_rev() -> str:
    return command("git", "rev-parse", "HEAD", use_stdout=True).out.decode().strip()


def stage_all() -> None:
    command("git", "add", "--all", ":/")


def commit(message: str) -> None:
    command("git", "commit", "--no-verify", "-m", message, stdout_on_stderr=True)


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("branch_name", nargs="?")
    parser.add_argument("-a", "--all", action="store_true")
    parser.add_argument("-p", "--print", action="store_true")

    return parser.parse_args()


def do_print(message: str, all: bool) -> None:
    current_commit = get_current_rev()

    if all:
        if has_staged_changes():
            commit("(staged changes)")
            staged_changes_commit = get_current_rev()

            command("git", "reset", "-q", current_commit)
        else:
            staged_changes_commit = current_commit

        stage_all()

        if has_staged_changes():
            commit(message)
            printed_commit = get_current_rev()
        else:
            printed_commit = current_commit
    else:
        if has_staged_changes():
            commit(message)
            printed_commit = get_current_rev()

            staged_changes_commit = printed_commit
        else:
            stage_all()

            if has_staged_changes():
                commit(message)
                printed_commit = get_current_rev()
            else:
                printed_commit = current_commit

            staged_changes_commit = current_commit

    command("git", "reset", "-q", staged_changes_commit)
    command("git", "reset", "-q", "--soft", current_commit)

    print(printed_commit)


def do_normal(message: str, all: bool) -> None:
    if all or not has_staged_changes():
        stage_all()

    if has_staged_changes():
        commit(message)

    if not all:
        command("git", "status")


def main(branch_name: str | None, all: bool, print: bool) -> None:
    if branch_name is None:
        branch_name = get_branch_name("HEAD")

        if branch_name is None:
            branch_name = "HEAD"

    message = f"({branch_name})"

    if print:
        do_print(message, all)
    else:
        do_normal(message, all)


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
