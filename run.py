#!/usr/bin/env python3
"""Zero-install launcher:  python run.py --help"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hollyweeb.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
