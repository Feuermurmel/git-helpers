import re
import shlex
from pathlib import Path
from subprocess import DEVNULL
from subprocess import check_call
from subprocess import run
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import NewType

from git_helpers.util import get_stripped_output

RebaseTodo = NewType("RebaseTodo", str)


def is_rebase_in_progress() -> bool:
    git_dir = Path(get_stripped_output(["git", "rev-parse", "--git-dir"]))

    return (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()


def git_rebase(base_arg: str, todo: RebaseTodo) -> None:
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


def get_rebase_todo(base_arg: str) -> RebaseTodo:
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

        return RebaseTodo(todo_file_path.read_text())


def edit_commit(todo: RebaseTodo, edit_commit_id: str) -> RebaseTodo:
    def repl_fn(match: re.Match[str]) -> str:
        if edit_commit_id.startswith(match.group("commit_id")):
            assert match.group("command").startswith(
                "p"
            ), f"Unexpected command for commit: {match.group()}"

            return f"edit {edit_commit_id}"
        else:
            return match.group()

    pattern = "^(?P<command>\\w+) (?P<commit_id>[a-z0-9]{7,})"
    return RebaseTodo(re.sub(pattern, repl_fn, todo, flags=re.MULTILINE))
