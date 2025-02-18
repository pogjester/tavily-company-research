from fastapi import WebSocket
from typing import Dict, Set
from datetime import datetime
import json

class ConnectionManager:
    def __init__(self):
        # Store active connections for each job
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, job_id: str):
        """Connect a new client to a specific job."""
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)
        
    def disconnect(self, websocket: WebSocket, job_id: str):
        """Disconnect a client from a specific job."""
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
                
    async def broadcast_to_job(self, job_id: str, message: dict):
        """Send a message to all clients connected to a specific job."""
        if job_id not in self.active_connections:
            return
            
        # Add timestamp to message
        message["timestamp"] = datetime.now().isoformat()
        
        # Convert message to JSON string
        message_str = json.dumps(message)
        
        # Send to all connected clients for this job
        disconnected = set()
        for connection in self.active_connections[job_id]:
            try:
                await connection.send_text(message_str)
            except Exception:
                disconnected.add(connection)
                
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection, job_id)
            
    async def send_status_update(self, job_id: str, status: str, progress: int, message: str = None, error: str = None, result: dict = None):
        """Helper method to send formatted status updates."""
        update = {
            "type": "status_update",
            "data": {
                "status": status,
                "progress": progress,
                "message": message,
                "error": error,
                "result": result
            }
        }
        await self.broadcast_to_job(job_id, update)
        
    async def send_analyst_update(self, job_id: str, analyst: str, queries: list[str]):
        """Helper method to send analyst query updates."""
        update = {
            "type": "analyst_update",
            "data": {
                "analyst": analyst,
                "queries": queries
            }
        }
        await self.broadcast_to_job(job_id, update) 