import argparse
import itertools
import os
import re
import subprocess
import sys

from git_helpers.util import UserError

_edit_env_variable_name = "GIT_SQUASH_EDIT"


def log(msg, *args):
    print(
        "{}: {}".format(os.path.basename(sys.argv[0]), msg.format(*args)),
        file=sys.stderr,
    )


def command(*args, return_exit_code=False, add_env={}):
    env = dict(os.environ)
    env.update(add_env)

    if return_exit_code:
        stdout = None
    else:
        stdout = subprocess.PIPE

    process = subprocess.Popen(args, stdout=stdout, env=env)
    output, _ = process.communicate()

    if return_exit_code:
        return process.returncode
    else:
        assert not process.returncode

        return output


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("rebase_base", nargs="?")
    parser.add_argument("-n", "--dry-run", action="store_true")

    return parser.parse_args()


def get_remote_refs():
    def iter_refs():
        for i in command("git", "show-ref").decode().splitlines():
            rev, ref = i.split(" ", 1)

            if re.match("refs/remotes/.*$", ref):
                yield rev

    return list(iter_refs())


def get_commits_not_reachable_by(base, other_commits):
    output = command("git", "rev-list", "--no-merges", base, "--not", *other_commits)

    return output.decode().splitlines()


def get_parent_commits(commit):
    output = command("git", "log", "-n", "1", "--pretty=%P", commit)

    return output.decode().split()


def get_commit_message(commit):
    output = command("git", "show", "--quiet", "--pretty=%s", commit)

    return output.decode().strip()


def group_commits_by_message(commits):
    commits_with_messages = [(i, get_commit_message(i)) for i in commits]
    commit_order = {c: i for i, (c, _) in enumerate(commits_with_messages)}
    message_order = {m: i for i, (_, m) in enumerate(commits_with_messages)}

    def sort_key(x):
        c, m = x

        return m.startswith("("), -message_order[m], -commit_order[c]

    def groupby_key(x):
        c, m = x

        return m

    sorted_commits = sorted(commits_with_messages, key=sort_key)
    grouped_commits = itertools.groupby(sorted_commits, key=groupby_key)

    return [list(x) for _, x in grouped_commits]


def rebase(base, commits, dry_run):
    def iter_todo_lines():
        for first, *rest in group_commits_by_message(commits):
            yield "p {} {}".format(*first)

            for i in rest:
                yield "f {} {}".format(*i)

    todo = "".join(i + "\n" for i in iter_todo_lines())

    if dry_run:
        print(todo)
    else:
        if base is None:
            base_arg = "--root"
        else:
            base_arg = base

        last_exit_code = command(
            "git",
            "rebase",
            "-i",
            base_arg,
            add_env={_edit_env_variable_name: todo, "GIT_SEQUENCE_EDITOR": __file__},
            return_exit_code=True,
        )

        while last_exit_code:
            assert last_exit_code == 1

            diff_exit_code = command(
                "git", "diff", "--quiet", "HEAD", return_exit_code=True
            )

            if diff_exit_code:
                raise UserError("A rebase operation failed.")

            last_exit_code = command("git", "rebase", "--skip", return_exit_code=True)


def command_main(rebase_base, dry_run):
    if rebase_base is None:
        other_commits = get_remote_refs()
    else:
        other_commits = [rebase_base]

    # Remove commit reachable by any of other_commits.
    rebased_commits = get_commits_not_reachable_by("HEAD", other_commits)

    if not rebased_commits:
        raise UserError("No commits left to rebase after removing the base commits.")

    parents = get_parent_commits(rebased_commits[-1])

    if not parents:
        base = None
    else:
        base = parents[0]

    rebase(base, rebased_commits, dry_run=dry_run)


def main():
    if _edit_env_variable_name in os.environ:
        with open(sys.argv[-1], "wb") as file:
            file.write(os.environ[_edit_env_variable_name].encode())
    else:
        command_main(**vars(parse_args()))


def entry_point():
    try:
        main()
    except UserError as e:
        log("Error: {}", e)
        sys.exit(1)
    except KeyboardInterrupt:
        log("Operation interrupted.")
        sys.exit(2)
