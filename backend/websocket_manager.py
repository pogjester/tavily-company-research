from fastapi import WebSocket
from typing import Dict, Set
from datetime import datetime
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        # Store active connections for each job
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, job_id: str):
        """Connect a new client to a specific job."""
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)
        logger.info(f"New WebSocket connection for job {job_id}")
        logger.info(f"Total connections for job: {len(self.active_connections[job_id])}")
        logger.info(f"All active jobs: {list(self.active_connections.keys())}")
        
    def disconnect(self, websocket: WebSocket, job_id: str):
        """Disconnect a client from a specific job."""
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
            logger.info(f"WebSocket disconnected for job {job_id}")
            logger.info(f"Remaining connections for job: {len(self.active_connections.get(job_id, set()))}")
            logger.info(f"Remaining active jobs: {list(self.active_connections.keys())}")
                
    async def broadcast_to_job(self, job_id: str, message: dict):
        """Send a message to all clients connected to a specific job."""
        if job_id not in self.active_connections:
            logger.warning(f"No active connections for job {job_id}")
            return
            
        # Add timestamp to message
        message["timestamp"] = datetime.now().isoformat()
        
        # Convert message to JSON string
        message_str = json.dumps(message)
        logger.info(f"Broadcasting message for job {job_id}")
        logger.info(f"Active connections for job: {len(self.active_connections[job_id])}")
        logger.info(f"Message content: {message_str}")
        
        # Send to all connected clients for this job
        success_count = 0
        disconnected = set()
        for connection in self.active_connections[job_id]:
            try:
                await connection.send_text(message_str)
                success_count += 1
            except Exception as e:
                logger.error(f"Error sending message to client: {str(e)}", exc_info=True)
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection, job_id)
            
    async def send_status_update(self, job_id: str, status: str, message: str = None, error: str = None, result: dict = None):
        """Helper method to send formatted status updates."""
        update = {
            "type": "status_update",
            "data": {
                "status": status,
                "message": message,
                "error": error,
                "result": result
            }
        }
        logger.info(f"Preparing status update for job {job_id}")
        logger.info(f"Status: {status}, Message: {message}")
        await self.broadcast_to_job(job_id, update)
        
    async def send_analyst_update(self, job_id: str, analyst: str, queries: list[str]):
        update = {
            "type": "analyst_update",
            "data": {
                "analyst": analyst,
                "queries": queries
            }
        }
        logger.info(f"Preparing analyst update for job {job_id}")
        logger.info(f"Analyst: {analyst}, Queries: {queries}")
        await self.broadcast_to_job(job_id, update) 