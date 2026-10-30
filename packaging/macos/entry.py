"""Frozen entry: dispatch multiprocessing children before importing Qt."""
import multiprocessing
import sys

if __name__ == '__main__':
    multiprocessing.freeze_support()
    if len(sys.argv) == 3 and sys.argv[1] == '--local-smoke-test':
        from smoke import run
        raise SystemExit(run(sys.argv[2]))
    from liltide.gui import main
    raise SystemExit(main())
