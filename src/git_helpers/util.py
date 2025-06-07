import logging
import shlex
import sys
from argparse import Namespace
from functools import wraps
from pathlib import Path
from subprocess import DEVNULL
from subprocess import PIPE
from subprocess import check_call
from subprocess import check_output
from subprocess import run
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Callable
from typing import overload


class UserError(Exception):
    pass


def pass_parsed_args(
    parse_args_fn: Callable[[], Namespace],
) -> Callable[[Callable[..., None]], Callable[[], None]]:
    def decorator_fn(main_fn: Callable[..., None]) -> Callable[[], None]:
        @wraps(main_fn)
        def main_fn_wrapper() -> None:
            logging.basicConfig(level=logging.INFO, format="%(message)s")

            try:
                main_fn(**vars(parse_args_fn()))
            except UserError as e:
                logging.error(f"error: {e}")
                sys.exit(1)
            except KeyboardInterrupt:
                logging.error("Operation interrupted.")
                sys.exit(130)

        return main_fn_wrapper

    return decorator_fn


@overload
def get_config(name: str, default: str) -> str: ...
@overload
def get_config(name: str) -> str | None: ...
def get_config(name: str, default: str | None = None) -> str | None:
    result = run(["git", "config", "--null", name], stdout=PIPE)
    values = result.stdout.split(b"\x00")[:-1]

    assert values or result.returncode

    if values:
        return values[0].decode()
    else:
        return default


def get_stripped_output(command: list[str]) -> str:
    return check_output(command, text=True).strip()


def get_commit_message(commit: str) -> str:
    output = check_output(["git", "show", "--quiet", "--pretty=%s", commit])

    return output.decode().strip()


def git_rebase(base_arg: str, todo: str) -> None:
    with TemporaryDirectory() as temp_dir:
        todo_file_path = Path(temp_dir) / "todo.txt"
        todo_file_path.write_text(todo)

        check_call(
            [
                "git",
                "-c",
                f"sequence.editor={shlex.join(['cp', str(todo_file_path)])}",
                "rebase",
                "--interactive",
                "--rebase-merges",
                "--empty=drop",
                base_arg,
            ]
        )


def get_rebase_todo(base_arg: str) -> str:
    with TemporaryDirectory() as temp_dir:
        todo_file_path = Path(temp_dir) / "todo.txt"

        sequence_editor_script = dedent(
            """\
            set -eu

            mv "$2" "$1"
            touch "$2"
            """
        )

        sequence_editor_command = [
            "bash",
            "-c",
            sequence_editor_script,
            "-",
            str(todo_file_path),
        ]

        run(
            [
                "git",
                "-c",
                f"sequence.editor={shlex.join(sequence_editor_command)}",
                "rebase",
                "--interactive",
                "--rebase-merges",
                base_arg,
            ],
            stderr=DEVNULL,
        )

        return todo_file_path.read_text()
