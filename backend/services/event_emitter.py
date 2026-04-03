import json
import uuid
import time
from fastapi import WebSocket
from typing import List, Optional


class EventEmitter:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def emit(
        self,
        run_id: str,
        node_id: str,
        type_str: str,
        input_str: str = "",
        output_str: str = "",
        metadata: dict | None = None,
        error: str = "",
    ):
        event = {
            "event_id": str(uuid.uuid4()),
            "run_id": run_id,
            "node_id": node_id,
            "type": type_str,
            "input": input_str,
            "output": output_str,
            "error": error,
            "metadata": metadata if metadata is not None else {},
            "timestamp": int(time.time() * 1000),
        }

        # Broadcast to all connected clients
        for ws in self.connections.copy():
            try:
                await ws.send_text(json.dumps(event))
            except Exception:
                self.disconnect(ws)


emitter = EventEmitter()
