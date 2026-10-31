import pytest


@pytest.fixture(autouse=True)
def _mock_only(live):
    if live:
        pytest.skip("self-tests build bad things, so they only run in mock mode")
