import logging
import os
import re
import subprocess
import sys
from argparse import ArgumentParser
from argparse import Namespace
from pathlib import Path

from git_helpers.util import UserError
from git_helpers.util import get_stripped_output

_edit_todo_env_name = "GIT_BISECTRUN_EDIT_TODO"


def is_rebase_in_progress() -> bool:
    git_dir = Path(get_stripped_output(["git", "rev-parse", "--git-dir"]))

    return (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()


def parse_args() -> Namespace:
    parser = ArgumentParser()

    parser.add_argument("-b", "--base", default="main")
    parser.add_argument("-e", "--edit", action="store_true")
    parser.add_argument("command", nargs="...")

    return parser.parse_args()


def main(base: str, edit: bool, command: list[str]) -> None:
    if is_rebase_in_progress():
        raise UserError("A rebase is currently in progress.")

    original_ref = get_stripped_output(
        ["git", "branch", "--show-current"]
    ) or get_stripped_output(["git", "rev-parse", "HEAD"])

    base_ref = get_stripped_output(["git", "merge-base", "HEAD", base])

    try:
        subprocess.check_call(["git", "bisect", "start", "HEAD", base_ref])
    except subprocess.CalledProcessError as e:
        raise UserError(f"{e}")
    else:
        try:
            subprocess.check_call(["git", "bisect", "run", *command])
        except subprocess.CalledProcessError:
            # An error message should have been printed.
            pass

        subprocess.check_call(["git", "checkout", original_ref])

        if edit:
            bad_ref = subprocess.check_output(
                ["git", "rev-parse", "refs/bisect/bad"], text=True
            ).strip()

            try:
                subprocess.check_call(
                    ["git", "rebase", "--interactive", "--rebase-merges", base_ref],
                    env={
                        **os.environ,
                        "GIT_SEQUENCE_EDITOR": __file__,
                        _edit_todo_env_name: bad_ref,
                    },
                )
            except subprocess.CalledProcessError:
                # An error message should have been printed.
                pass


def edit_todo(todo_str: str, edit_commit_id: str) -> str:
    def repl_fn(match: re.Match[str]) -> str:
        if edit_commit_id.startswith(match.group("commit_id")):
            assert match.group("command").startswith(
                "p"
            ), f"Unexpected command for commit: {match.group()}"

            return f"edit {edit_commit_id}"
        else:
            return match.group()

    return re.sub(
        "^(?P<command>\\w+) (?P<commit_id>[a-z0-9]{7,})",
        repl_fn,
        todo_str,
        flags=re.MULTILINE,
    )


def todo_editor_main(todo_path_str: str) -> None:
    todo_path = Path(todo_path_str)
    edit_commit_id = os.environ[_edit_todo_env_name]

    todo_path.write_text(edit_todo(todo_path.read_text(), edit_commit_id))


def entry_point() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        if _edit_todo_env_name in os.environ:
            todo_editor_main(*sys.argv[1:])
        else:
            main(**vars(parse_args()))
    except UserError as e:
        logging.error(f"error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.error("Operation interrupted.")
        sys.exit(130)
