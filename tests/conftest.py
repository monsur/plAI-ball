import os
import sys
import types
import logging
import pytest

# Patch sys.argv before any podcaster imports trigger argparse via logger_helper.
# logger_helper imports args_helper and calls get_args() on first use, which
# invokes argparse.parse_args() — that would fail under pytest without this.
sys.argv = [sys.argv[0]]

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def read_fixture(filename):
    """Read a fixture file and return its contents as a string."""
    with open(os.path.join(FIXTURES_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def mock_args(tmp_path):
    """Create a mock args namespace matching what args_helper.get_args() returns."""
    output_dir = str(tmp_path / "output" / "20250501")
    output_data_dir = str(tmp_path / "output" / "20250501" / "data")
    output_log_dir = str(tmp_path / "output" / "20250501" / "logs")
    os.makedirs(output_data_dir, exist_ok=True)
    os.makedirs(output_log_dir, exist_ok=True)

    args = types.SimpleNamespace(
        date="20250501",
        delay=0,
        model="OpenAI",
        prettyprint=False,
        s3_bucket="plai-ball",
        output_root=str(tmp_path / "output"),
        output_dir=output_dir,
        output_data_dir=output_data_dir,
        output_log_dir=output_log_dir,
    )
    return args
