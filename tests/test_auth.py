import pytest
from pydantic import ValidationError

from authentication.user.request import UserRequest

from authentication.user.utils import create_access_token, decode_access_token

def test_request_validation_rejects_short_password():

    with pytest.raises(ValidationError):
        UserRequest(username="alice", email="alice@example.com", password="short")


def test_access_token_round_trip(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "0123456789abcdef0123456789abcdef")


    token = create_access_token({"sub": "alice@example.com"})

    assert decode_access_token(token)["sub"] == "alice@example.com"