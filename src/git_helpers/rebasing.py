import re
import shlex
from pathlib import Path
from subprocess import DEVNULL
from subprocess import check_call
from subprocess import run
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import NewType

from git_helpers.git import Rev
from git_helpers.git import get_first_parent
from git_helpers.util import UserError
from git_helpers.util import get_stripped_output

RebaseTodo = NewType("RebaseTodo", str)


def is_rebase_in_progress() -> bool:
    git_dir = Path(get_stripped_output(["git", "rev-parse", "--git-dir"]))

    return (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()


def _rebase_base_arg(base_ref: str | None) -> str:
    if base_ref is None:
        return "--root"
    else:
        return base_ref


def git_rebase(base: str | None, todo: RebaseTodo) -> None:
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
                _rebase_base_arg(base),
            ]
        )


def get_rebase_todo(base: str | None) -> RebaseTodo:
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
                _rebase_base_arg(base),
            ],
            stderr=DEVNULL,
        )

        return RebaseTodo(todo_file_path.read_text())


def edit_commit(commit: Rev) -> None:
    def repl_fn(match: re.Match[str]) -> str:
        if commit.startswith(match.group("commit_id")):
            if not match.group("command").startswith("p"):
                if match.group("command").endswith("-C"):
                    raise UserError(
                        f"Commit {commit} is a merge commit and can't be edited."
                    )

                raise Exception(f"Unexpected command for commit: {match.group()}")

            return f"edit {commit}"
        else:
            return match.group()

    parent = get_first_parent(commit)
    todo = get_rebase_todo(parent)

    # This should be replaced with instead excluding the edited commit from
    # the rebased commits and starting the todo list with a `break` command.
    # https://github.com/fork-dev/Tracker/issues/2370
    pattern = "^(?P<command>\\w+( -C)?) (?P<commit_id>[a-z0-9]{7,})"
    todo = RebaseTodo(re.sub(pattern, repl_fn, todo, flags=re.MULTILINE))

    git_rebase(parent, todo)
