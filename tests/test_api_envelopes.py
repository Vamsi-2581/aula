"""Aula rejections must not become successful empty reader results."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from aula.api_client import AulaApiClient
from aula.http import AulaInvalidTokenError, AulaStepUpRequiredError, HttpRequestError, HttpResponse


def client_with_responses(*responses, refresh=None):
    http = AsyncMock()
    http.request.side_effect = list(responses)
    http.get_cookie = MagicMock(return_value=None)
    return AulaApiClient(http, on_token_refresh=refresh)


@pytest.mark.asyncio
@pytest.mark.parametrize("reader", ["calendar", "folders"])
@pytest.mark.parametrize("code", [1, 987])
async def test_explicit_rejection_raises_with_method_and_code(reader, code):
    client = client_with_responses(HttpResponse(200, {"status": {"code": code}, "data": []}))
    with pytest.raises(HttpRequestError, match=f"{code}") as exc:
        if reader == "calendar":
            await client.get_calendar_events([100], datetime(2026, 3, 1), datetime(2026, 3, 1))
        else:
            await client.get_message_folders()
    assert ("calendar." if reader == "calendar" else "messaging.") in str(exc.value)


@pytest.mark.asyncio
async def test_successful_empty_calendar_is_valid():
    client = client_with_responses(HttpResponse(200, {"status": {"code": 0}, "data": []}))
    assert await client.get_calendar_events([100], datetime(2026, 3, 1), datetime(2026, 3, 1)) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "subcode,error", [(9, AulaInvalidTokenError), (8, AulaStepUpRequiredError)]
)
async def test_known_auth_subcodes_keep_specific_errors(subcode, error):
    client = client_with_responses(HttpResponse(200, {"status": {"code": 1, "subCode": subcode}}))
    with pytest.raises(error):
        await client.get_message_folders()


@pytest.mark.asyncio
async def test_recovered_auth_envelope_returns_successful_reader_result():
    ok = HttpResponse(200, {"status": {"code": 0}, "data": []})
    refresh = AsyncMock(return_value="new-token")
    client = client_with_responses(
        HttpResponse(200, {"status": {"code": 1, "subCode": 9}}), ok, ok, ok, refresh=refresh
    )
    assert await client.get_calendar_events([100], datetime(2026, 3, 1), datetime(2026, 3, 1)) == []
    refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_vendor_shape_is_not_validated_as_an_aula_envelope():
    response = HttpResponse(200, {"status": {"code": 999}, "data": []})
    client = client_with_responses(response)
    assert (
        await client._request_with_version_retry("get", "https://vendor.example/data") is response
    )
