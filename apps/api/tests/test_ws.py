"""WebSocket endpoint tests."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from app.core.security import create_access_token
from app.main import app
from app.models.user import User, UserRole

FAKE_UID = uuid.uuid4()
FAKE_CID = uuid.uuid4()


def _fake_user() -> MagicMock:
    u = MagicMock(spec=User)
    u.id = FAKE_UID
    u.company_id = FAKE_CID
    u.is_active = True
    u.role = UserRole.CEO
    return u


def _valid_token() -> str:
    return create_access_token(str(FAKE_UID))


# ─── Invalid / missing token ──────────────────────────────────────────────────

def test_ws_rejects_invalid_token():
    """Connection with a bad JWT is rejected (WebSocketDisconnect or HTTP error)."""
    rejected = False
    with TestClient(app, raise_server_exceptions=False) as client:
        try:
            with client.websocket_connect("/api/v1/ws?token=not_a_jwt") as ws:
                ws.receive_text()
        except Exception:
            rejected = True
    assert rejected


def test_ws_rejects_refresh_token():
    """Refresh tokens must be rejected (wrong token type)."""
    from app.core.security import create_refresh_token
    refresh_token, _ = create_refresh_token(str(FAKE_UID))
    rejected = False
    with TestClient(app, raise_server_exceptions=False) as client:
        try:
            with client.websocket_connect(f"/api/v1/ws?token={refresh_token}") as ws:
                ws.receive_text()
        except Exception:
            rejected = True
    assert rejected


# ─── Happy path: accepted + event relay ───────────────────────────────────────

def test_ws_accepts_valid_token_and_relays_event():
    """Valid JWT → accepted; Redis pub/sub message is forwarded to the client."""
    token = _valid_token()

    async def _listen():
        yield {"type": "subscribe", "channel": "x", "data": 1}
        yield {
            "type": "message",
            "channel": "x",
            "data": json.dumps({"type": "alert", "data": {"anomalies_found": 2}}),
        }

    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.listen = _listen  # async generator factory

    mock_redis_conn = MagicMock()
    mock_redis_conn.pubsub.return_value = mock_pubsub
    mock_redis_conn.aclose = AsyncMock()

    mock_db = AsyncMock()
    mock_db.scalar = AsyncMock(return_value=_fake_user())

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.api.v1.endpoints.ws.aioredis.from_url", return_value=mock_redis_conn),
        patch("app.api.v1.endpoints.ws.AsyncSessionLocal", return_value=mock_ctx),
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            with client.websocket_connect(f"/api/v1/ws?token={token}") as ws:
                data = ws.receive_text()

    msg = json.loads(data)
    assert msg["type"] == "alert"
    assert msg["data"]["anomalies_found"] == 2
