import logging
import re
import sys
from argparse import ArgumentParser
from argparse import Namespace
from pathlib import Path
from subprocess import CalledProcessError
from subprocess import check_call
from subprocess import check_output

from git_helpers.util import UserError
from git_helpers.util import get_rebase_todo
from git_helpers.util import get_stripped_output
from git_helpers.util import git_rebase


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
        check_call(["git", "bisect", "start", "HEAD", base_ref])
    except CalledProcessError as e:
        raise UserError(f"{e}")
    else:
        try:
            check_call(["git", "bisect", "run", *command])
        except CalledProcessError:
            # An error message should have been printed.
            pass

        check_call(["git", "checkout", original_ref])

        if edit:
            bad_ref = check_output(
                ["git", "rev-parse", "refs/bisect/bad"], text=True
            ).strip()
            todo = edit_todo(get_rebase_todo(base_ref), bad_ref)

            try:
                git_rebase(base_ref, todo)
            except CalledProcessError as e:
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
