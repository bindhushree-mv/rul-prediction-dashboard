import asyncio
import json
import os
from collections import deque
from datetime import datetime
import boto3
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any

ALERT_THRESHOLD = 30
MAX_HISTORY = 100
REGION = "us-east-1"

readings_history = deque(maxlen=MAX_HISTORY)
alerts_history = deque(maxlen=50)
latest_reading = {}
connected_clients = []
alert_sent_units = set()

app = FastAPI(title="RUL Dashboard API")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class Reading(BaseModel):
    unit_id: int
    cycle: int
    predicted_RUL: float
    sensors: dict
    timestamp: str = ""

async def broadcast(message):
    disconnected = []
    text = json.dumps(message)
    for client in connected_clients:
        try:
            await client.send_text(text)
        except Exception:
            disconnected.append(client)
    for c in disconnected:
        if c in connected_clients:
            connected_clients.remove(c)

@app.post("/ingest")
async def ingest(reading: Reading):
    global latest_reading
    data = reading.dict()
    data["server_time"] = datetime.utcnow().isoformat()
    readings_history.append(data)
    latest_reading = data
    rul = data.get("predicted_RUL", 999)
    unit_id = data.get("unit_id")
    print(f"  Ingested Unit {unit_id} Cycle {data.get('cycle')} RUL {rul:.1f}", flush=True)
    if rul < ALERT_THRESHOLD and unit_id not in alert_sent_units:
        alert_record = {"unit_id": unit_id, "rul": rul,
                        "cycle": data.get("cycle"), "time": data["server_time"]}
        alerts_history.append(alert_record)
        alert_sent_units.add(unit_id)
        print(f"  ALERT for Engine {unit_id}!", flush=True)
    await broadcast(data)
    return {"status": "ok"}

@app.get("/")
def root():
    return {"status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy", "clients": len(connected_clients),
            "readings": len(readings_history), "alerts": len(alerts_history)}

@app.get("/latest")
def get_latest():
    return latest_reading if latest_reading else {"message": "No data yet"}

@app.get("/history")
def get_history(limit: int = 100):
    data = list(readings_history)[-limit:]
    return {"count": len(data), "readings": data}

@app.get("/alerts")
def get_alerts():
    return {"count": len(alerts_history), "alerts": list(alerts_history)}

@app.get("/status")
def get_status():
    return {"connected_clients": len(connected_clients),
            "total_readings": len(readings_history),
            "total_alerts": len(alerts_history),
            "latest_unit": latest_reading.get("unit_id"),
            "latest_rul": latest_reading.get("predicted_RUL"),
            "latest_cycle": latest_reading.get("cycle"),
            "server_time": datetime.utcnow().isoformat()}

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    print(f"WebSocket connected (total: {len(connected_clients)})", flush=True)
    if readings_history:
        await websocket.send_text(json.dumps({
            "type": "history",
            "readings": list(readings_history)[-20:]
        }))
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
