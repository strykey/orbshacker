"""Entry point for `python -m orbshacker`."""

import sys

if "--timer-mode" in sys.argv:
    from .timer import run_timer

    run_timer()
else:
    from .main import main

    main()
