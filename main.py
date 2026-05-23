import sys
from pathlib import Path

# Ensure our own package is found first
_src = Path(__file__).resolve().parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from educoder_cli.cli import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()
