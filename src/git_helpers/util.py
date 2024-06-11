import subprocess
from typing import overload


class UserError(Exception):
    pass


@overload
def get_config(name: str, default: str) -> str: ...
@overload
def get_config(name: str) -> str | None: ...
def get_config(name: str, default: str | None = None) -> str | None:
    result = subprocess.run(["git", "config", "--null", name], stdout=subprocess.PIPE)
    values = result.stdout.split(b"\x00")[:-1]

    assert values or result.returncode

    if values:
        return values[0].decode()
    else:
        return default


def get_stripped_output(command: list[str]) -> str:
    return subprocess.check_output(command).strip().decode()
