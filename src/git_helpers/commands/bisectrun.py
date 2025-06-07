from argparse import ArgumentParser
from argparse import Namespace
from subprocess import CalledProcessError
from subprocess import check_call
from subprocess import check_output

from git_helpers.rebasing import edit_commit
from git_helpers.rebasing import is_rebase_in_progress
from git_helpers.util import UserError
from git_helpers.util import get_stripped_output
from git_helpers.util import pass_parsed_args


def parse_args() -> Namespace:
    parser = ArgumentParser()

    parser.add_argument("-b", "--base", default="main")
    parser.add_argument("-e", "--edit", action="store_true")
    parser.add_argument("command", nargs="...")

    return parser.parse_args()


@pass_parsed_args(parse_args)
def entry_point(base: str, edit: bool, command: list[str]) -> None:
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

            try:
                edit_commit(bad_ref)
            except CalledProcessError as e:
                # An error message should have been printed.
                pass
