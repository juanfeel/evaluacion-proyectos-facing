import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken


@pytest.fixture
def api_client():
    return APIClient()


def cliente_de(usuario) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(usuario)}")
    return client


@pytest.fixture
def admin_client(db):
    from .factories import AdminFactory

    return cliente_de(AdminFactory())
