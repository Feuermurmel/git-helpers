import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from git_helpers.util import UserError

_edit_todo_env_name = "GIT_BISECTRUN_EDIT_TODO"


def log(message):
    print(message, file=sys.stderr, flush=True)


def get_config(name):
    result = subprocess.run(["git", "config", "--null", name], stdout=subprocess.PIPE)
    values = result.stdout.split(b"\x00")[:-1]

    if values:
        assert not result.returncode

        (value,) = values

        return value.decode()
    else:
        assert result.returncode

        return None


def get_stripped_output(command):
    return subprocess.check_output(command).strip().decode()


def is_rebase_in_progress():
    git_dir = Path(get_stripped_output(["git", "rev-parse", "--git-dir"]))

    return (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-b", "--base", default="main")
    parser.add_argument("-e", "--edit", action="store_true")
    parser.add_argument("command", nargs="...")

    return parser.parse_args()


def main(base, edit, command):
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


def edit_todo(todo_str, edit_commit_id):
    def repl_fn(match):
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


def todo_editor_main(todo_path):
    todo_path = Path(todo_path)
    edit_commit_id = os.environ[_edit_todo_env_name]

    todo_path.write_text(edit_todo(todo_path.read_text(), edit_commit_id))


def entry_point():
    try:
        if _edit_todo_env_name in os.environ:
            todo_editor_main(*sys.argv[1:])
        else:
            main(**vars(parse_args()))
    except KeyboardInterrupt:
        log("Operation interrupted.")
        sys.exit(1)
    except UserError as e:
        log(f"error: {e}")
        sys.exit(2)
