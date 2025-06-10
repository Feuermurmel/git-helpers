import re
from collections.abc import Iterator
from subprocess import PIPE
from subprocess import call
from subprocess import check_output
from subprocess import run
from typing import NewType
from typing import cast
from typing import overload

# A 40-digit hex commit ID.
Rev = NewType("Rev", str)


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


def resolve_rev(ref: str) -> Rev:
    return Rev(
        check_output(
            ["git", "rev-parse", "--verify", "--end-of-options", ref, "--"], text=True
        ).strip()
    )


def get_commit_message(ref: str) -> str:
    output = check_output(["git", "show", "--quiet", "--pretty=%s", ref])

    return output.decode().strip()


def ref_exists(ref: str) -> bool:
    return call(["git", "rev-parse", "--verify", "--quiet", "HEAD"]) == 0


def get_remote_refs() -> list[str]:
    def iter_refs() -> Iterator[str]:
        for i in check_output(["git", "show-ref"], text=True).splitlines():
            rev, ref = i.split(" ", 1)

            if re.match("refs/remotes/.*$", ref):
                yield rev

    return list(iter_refs())


def get_commits_not_reachable_by(base: str, other_refs: list[str]) -> list[str]:
    return check_output(
        ["git", "rev-list", "--no-merges", base, "--not", *other_refs], text=True
    ).splitlines()


def get_parent_commits(ref: str) -> list[Rev]:
    return cast(
        list[Rev],
        check_output(["git", "log", "-n", "1", "--pretty=%P", ref], text=True).split(),
    )


def get_first_parent(ref: str) -> Rev | None:
    parents = get_parent_commits(ref)

    if parents:
        return parents[0]
    else:
        return None


def get_branch_name(ref: str) -> str | None:
    result = run(["git", "symbolic-ref", "-q", "--short", ref], stdout=PIPE)

    if result.returncode:
        return None
    else:
        return result.stdout.decode().strip()


def has_staged_changes() -> bool:
    return run(["git", "diff", "--cached", "--quiet"]).returncode > 0


def stage_all() -> None:
    run(["git", "add", "--all", ":/"])
