import pytest
import spyne.util.appreg as appreg


@pytest.fixture(autouse=True)
def clear_app_registry():
    yield
    appreg.applications.clear()
