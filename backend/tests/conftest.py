import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client for integration tests."""
    return TestClient(app)


@pytest.fixture(params=[
    "Front Office",
    "Billing & Cash Operations",
    "Insurance & TPA",
    "IT & HIS Support",
    "Operations Management",
])
def role(request):
    """Representative hospital roles for parameterized tests."""
    return request.param
