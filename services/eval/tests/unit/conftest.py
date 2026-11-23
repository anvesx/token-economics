import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))  # tests are imported by file path, so share the fakes this way

from fakes import World  # noqa: E402


@pytest.fixture
def world() -> World:
    return World()
