from __future__ import annotations

import argparse

from ai_impact_research import __version__


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Impact Research CLI")
    parser.add_argument("--version", action="store_true", help="Print package version")
    args = parser.parse_args()
    if args.version:
        print(__version__)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
