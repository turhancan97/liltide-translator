"""Optional Qt entry point. Importing the CLI never imports Qt."""

import multiprocessing
import sys


def main():
    multiprocessing.freeze_support()
    try:
        from liltide.gui_window import launch
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith('PySide6'):
            print('GUI dependency missing. Install with: python -m pip install -e ".[gui]"', file=sys.stderr)
            return 1
        raise
    return launch()


if __name__ == '__main__':
    raise SystemExit(main())
