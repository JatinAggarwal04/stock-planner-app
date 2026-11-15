"""Backend authentication: Supabase token verification and the 12-hour sign-in limit."""
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

import main
from tests.conftest import auth_headers, make_token

PROTECTED = [
    ("get", "/analyze/TEST.NS"),
    ("get", "/analyze/TEST.NS/personalized?buy_price=10&quantity=1"),
    ("get", "/search?query=tcs"),
    ("get", "/history/TEST.NS"),
    ("get", "/quote/TEST.NS"),
    ("post", "/api/chat"),
]


def call(client, method, path, headers=None):
    if method == "post":
        return client.post(path, json={"message": "hi"}, headers=headers)
    return client.get(path, headers=headers)


@pytest.mark.parametrize("method, path", PROTECTED)
def test_protected_endpoints_need_a_signed_in_user(anon_client, method, path):
    response = call(anon_client, method, path)
    assert response.status_code == 401
    assert response.json() == {"detail": "Not signed in"}


@pytest.mark.parametrize("method, path", PROTECTED)
def test_session_older_than_12_hours_is_rejected(anon_client, method, path):
    response = call(anon_client, method, path, headers=auth_headers(signed_in_ago=13 * 3600))
    assert response.status_code == 401
    assert "expired" in response.json()["detail"]


def test_session_within_12_hours_is_accepted(anon_client):
    response = anon_client.get("/quote/TEST.NS", headers=auth_headers(signed_in_ago=11 * 3600))
    assert response.status_code == 200


@pytest.mark.parametrize(
    "headers",
    [
        {"Authorization": "Bearer not-a-jwt"},
        {"Authorization": "Basic abc"},
        {"Authorization": f"Bearer {make_token(expires_in=-60)}"},  # access token expired
        {"Authorization": f"Bearer {make_token(aud='anon')}"},  # wrong audience
        {"Authorization": f"Bearer {make_token(key=ec.generate_private_key(ec.SECP256R1()))}"},  # forged signature
        {"Authorization": f"Bearer {make_token(amr=[])}"},  # no sign-in time
    ],
)
def test_invalid_tokens_are_rejected(anon_client, headers):
    assert anon_client.get("/quote/TEST.NS", headers=headers).status_code == 401


def test_hs256_token_signed_with_public_key_is_rejected(anon_client):
    # Algorithm-confusion attempt: only asymmetric algorithms are accepted
    token = jwt.encode({"sub": "x", "aud": "authenticated", "exp": 9999999999}, "secret", algorithm="HS256")
    assert anon_client.get("/quote/TEST.NS", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_unconfigured_auth_fails_closed(anon_client, monkeypatch):
    monkeypatch.setattr(main, "_jwks_client", None)
    assert anon_client.get("/quote/TEST.NS", headers=auth_headers()).status_code == 503


def test_jwks_outage_is_503_not_logout(anon_client, monkeypatch):
    class Down:
        def get_signing_key_from_jwt(self, token):
            raise jwt.PyJWKClientConnectionError("unreachable")

    monkeypatch.setattr(main, "_jwks_client", Down())
    assert anon_client.get("/quote/TEST.NS", headers=auth_headers()).status_code == 503


def test_public_endpoints_stay_open(anon_client):
    assert anon_client.get("/").status_code == 200
    assert anon_client.post("/admin/train-universal").status_code == 403  # admin key, not user auth
