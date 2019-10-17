# -*- coding: utf-8 -*-
from unittest.mock import patch, MagicMock, call

from keycloak.constants import GrantTypes
from keycloak.utils import auth_header


def test_no_login(flask_client):
    response = flask_client.get("/howdy")
    assert response.status_code == 302
    assert response.headers["Location"] == "http://localhost/kc/login"


def test_login(flask_client):
    response = flask_client.get("/kc/login")
    assert response.status_code == 302


@patch("keycloak.mixins.authentication.requests.post")
@patch("keycloak.mixins.authentication.uuid4")
@patch("keycloak.extensions.flask.session")
def test_callback(mock_session, mock_uuid4, mock_post, flask_client, kc_config):
    mock_session.pop.return_value = "state123"
    mock_uuid4.return_value = MagicMock()
    mock_uuid4.return_value.hex.return_value = "0123456789"
    mock_post.return_value = MagicMock()
    mock_post.return_value.json.return_value = {"access_token": "token123"}
    token_endpoint_payload = {
        "code": "code123",
        "grant_type": GrantTypes.authorization_code,
        "client_id": kc_config.client.client_id,
        "redirect_uri": kc_config.client.redirect_uri,
        "client_secret": kc_config.client.client_secret,
    }
    userinfo_endpoint_header = auth_header("token123")
    expected_calls = [
        call(kc_config.openid.token_endpoint, data=token_endpoint_payload),
        call().raise_for_status(),
        call().json(),
        call(kc_config.openid.userinfo_endpoint, headers=userinfo_endpoint_header),
        call().raise_for_status(),
        call().json(),
    ]
    response = flask_client.get("/kc/callback?state=state123&code=code123")
    assert response.status_code == 302
    mock_post.assert_has_calls(expected_calls)


@patch("keycloak.extensions.flask.session")
def test_invalid_callback(mock_session, flask_client):
    mock_session.pop.return_value = "unknown"
    response = flask_client.get("/kc/callback?state=state123&code=code123")
    assert response.status_code == 403