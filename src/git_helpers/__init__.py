import logging
import sys
from argparse import ArgumentParser
from argparse import Namespace
from pathlib import Path

from git_helpers.util import UserError


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("files", type=Path, nargs="+")

    return parser.parse_args()


def main(paths: list[Path]) -> None:
    print(paths)


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
