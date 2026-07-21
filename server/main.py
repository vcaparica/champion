"""
server/main.py - Champion game server entry point
===================================================
FastAPI WebSocket server for matchmaking and combat resolution.
Run with: uvicorn server.main:app --host 0.0.0.0 --port 8000
"""
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from server.session import SessionManager
from server.match_manager import MatchManager
from server.client_handler import handle_message

app = FastAPI(title="Champion Game Server")
session_manager = SessionManager()
match_manager = MatchManager()


@app.get("/health")
async def health():
    return {"status": "ok", "players": len(session_manager.get_active_sessions())}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    player_name = f"Player_{len(session_manager.get_active_sessions()) + 1}"
    session = session_manager.create_session(player_name, websocket)

    try:
        await websocket.send_json({"type": "connected", "player_id": session.player_id})

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            response = await handle_message(session, message, match_manager, session_manager)
            await websocket.send_json(response)

    except WebSocketDisconnect:
        session_manager.remove_session(session.player_id)
    except Exception:
        session_manager.remove_session(session.player_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
