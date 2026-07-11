import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests that call Azure API "
    )

def pytest_collection_modifyitems(config, items):
    if not config.getoption("--integration"):
        skip_integration = pytest.mark.skip(reason="Pass --integration to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)