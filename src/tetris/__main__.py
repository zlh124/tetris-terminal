"""Allow ``python -m tetris`` to launch the game."""

import sys

from tetris.cli import main

sys.exit(main())
