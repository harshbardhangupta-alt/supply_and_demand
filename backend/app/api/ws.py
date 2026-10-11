"""WebSocket live updates (overview, positions, engine status).

The frontend uses this for push updates and falls back to REST polling when the
socket is unavailable.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..runtime import get_state

router = APIRouter()


@router.websocket("/ws/stream")
async def stream(ws: WebSocket):
    await ws.accept()
    st = get_state()
    try:
        while True:
            payload = {
                "type": "tick",
                "overview": st.overview(),
                "positions": [
                    {"symbol": p.symbol, "side": p.side.value, "qty": p.qty,
                     "unrealized_pnl": round(p.unrealized_pnl, 2)}
                    for p in st.paper_broker.positions()
                ],
            }
            await ws.send_json(payload)
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        return
    except Exception:
        await ws.close()
