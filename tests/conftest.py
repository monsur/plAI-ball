import os
import sys
import types
import logging
from pathlib import Path
import pytest

# Patch sys.argv before any podcaster imports trigger argparse via logger_helper.
# logger_helper imports args_helper and calls get_args() on first use, which
# invokes argparse.parse_args() — that would fail under pytest without this.
sys.argv = [sys.argv[0]]

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def read_fixture(filename):
    """Read a fixture file and return its contents as a string."""
    return (FIXTURES_DIR / filename).read_text(encoding="utf-8")


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def mock_args(tmp_path):
    """Create a mock args namespace matching what args_helper.get_args() returns."""
    output_dir = tmp_path / "output" / "20250501"
    output_data_dir = output_dir / "data"
    output_log_dir = output_dir / "logs"
    output_data_dir.mkdir(parents=True, exist_ok=True)
    output_log_dir.mkdir(parents=True, exist_ok=True)

    args = types.SimpleNamespace(
        date="20250501",
        delay=0,
        model="OpenAI",
        prettyprint=False,
        s3_bucket="plai-ball",
        output_root=tmp_path / "output",
        output_dir=output_dir,
        output_data_dir=output_data_dir,
        output_log_dir=output_log_dir,
    )
    return args
