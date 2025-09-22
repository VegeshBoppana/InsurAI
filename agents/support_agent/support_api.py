# agents/support_agent/support_api.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from agents.support_agent.support_graph import support_app, SupportState

router = APIRouter()

# In-memory session storage (simple for now)
user_sessions: Dict[str, Dict[str, Any]] = {}


class SupportRequest(BaseModel):
    session_id: str
    user_query: str


@router.post("/support/start")
def start_session(session_id: str):
    """
    Start a new support session for a given session_id.
    """
    if session_id in user_sessions:
        raise HTTPException(status_code=400, detail="Session already exists")
    user_sessions[session_id] = SupportState()
    return {"message": f"Support session {session_id} started."}


@router.post("/support/query")
def process_query(request: SupportRequest):
    """
    Process a user query inside a session.
    """
    session_id = request.session_id
    user_query = request.user_query

    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="Session not found. Please start a session first.")

    # Update session state with query
    state = user_sessions[session_id]
    state["user_query"] = user_query

    # Run through support graph
    try:
        updated_state = support_app.invoke(state)
        user_sessions[session_id] = updated_state

        return {
            "response": updated_state.get("conversation", [])[-1]["content"] if updated_state.get("conversation") else "I'm here to help!",
            "session_state": updated_state
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {e}")


@router.post("/support/end")
def end_session(session_id: str):
    """
    End a support session and clean up.
    """
    if session_id not in user_sessions:
        raise HTTPException(status_code=404, detail="Session not found.")

    state = user_sessions.pop(session_id)
    state["session_complete"] = True

    return {"message": f"Support session {session_id} ended.", "final_state": state}
