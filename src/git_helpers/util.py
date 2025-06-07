import logging
import sys
from argparse import Namespace
from functools import wraps
from subprocess import check_output
from typing import Callable


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


def get_stripped_output(command: list[str]) -> str:
    return check_output(command, text=True).strip()
