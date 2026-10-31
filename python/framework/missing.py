import os

import pytest


def missing(reason):
    """A missing tool is a skip on a laptop, but a failure in the pipeline."""
    if os.environ.get("CI"):
        pytest.fail(reason)
    pytest.skip(reason)
