"""`python -m token_economics_app_worker` and the `token-economics-worker` script."""

import sys

from .worker import main

if __name__ == "__main__":
    sys.exit(main())
