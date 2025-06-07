import argparse
import subprocess
import sys
from argparse import Namespace
from subprocess import PIPE
from typing import IO
from typing import Any

from git_helpers.util import get_commit_message
from git_helpers.util import pass_parsed_args


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
    args = ["--no-verify", "-m", message]

    if message == get_commit_message("HEAD"):
        args.append("--amend")

    command("git", "commit", *args, stdout_on_stderr=True)


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

    command("git", "status")
