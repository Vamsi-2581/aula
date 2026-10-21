"""OAuth callback validation against an offline token endpoint."""

from urllib.parse import parse_qs

import httpx
import pytest

from aula.auth.exceptions import OAuthError
from aula.auth.mitid_client import MitIDAuthClient
from aula.const import APP_REDIRECT_URI


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query", ["code=example", "code=example&state=", "code=example&state=wrong"]
)
async def test_invalid_callback_state_never_requests_tokens(query):
    requests = []

    def endpoint(request):
        requests.append(request)
        return httpx.Response(200, json={"access_token": "new-token"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(endpoint)) as http:
        client = MitIDAuthClient("tester", httpx_client=http)
        client._state = "expected-state"
        with pytest.raises(OAuthError, match="[Ss]tate"):
            await client._step7_exchange_oauth_code(f"{APP_REDIRECT_URI}?{query}")
    assert requests == []


@pytest.mark.asyncio
async def test_matching_callback_state_exchanges_code_with_pkce():
    requests = []

    def endpoint(request):
        requests.append(request)
        return httpx.Response(200, json={"access_token": "new-token", "expires_in": 3600})

    async with httpx.AsyncClient(transport=httpx.MockTransport(endpoint)) as http:
        client = MitIDAuthClient("tester", httpx_client=http)
        client._state = "expected-state"
        client._code_verifier = "pkce-verifier"
        tokens = await client._step7_exchange_oauth_code(
            f"{APP_REDIRECT_URI}?code=example&state=expected-state"
        )
        assert tokens["access_token"] == client.access_token == "new-token"
    assert len(requests) == 1
    assert parse_qs(requests[0].content.decode())["code_verifier"] == ["pkce-verifier"]


@pytest.mark.asyncio
async def test_callback_without_code_is_rejected():
    def endpoint(request):
        pytest.fail("Missing-code callback must not reach token endpoint")

    async with httpx.AsyncClient(transport=httpx.MockTransport(endpoint)) as http:
        client = MitIDAuthClient("tester", httpx_client=http)
        client._state = "expected-state"
        with pytest.raises(OAuthError, match="No authorization code"):
            await client._step7_exchange_oauth_code(f"{APP_REDIRECT_URI}?state=expected-state")
