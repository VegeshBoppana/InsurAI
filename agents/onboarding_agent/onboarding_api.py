from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents.onboarding_agent.onboarding_graph import onboarding_app, OnboardingState
import uvicorn

app = FastAPI(title="InsurAI Onboarding API", version="1.0")

# In-memory session store (for demo, you can switch to Redis/DB later)
sessions = {}


class UserInput(BaseModel):
    session_id: str
    message: str


@app.post("/onboarding/start")
def start_onboarding(session_id: str):
    """
    Start a new onboarding session.
    """
    if session_id in sessions:
        raise HTTPException(status_code=400, detail="Session already exists")
    sessions[session_id] = {}
    return {"message": "Onboarding session started", "session_id": session_id}


@app.post("/onboarding/next")
def continue_onboarding(user_input: UserInput):
    """
    Continue an onboarding session with the user's message.
    """
    if user_input.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    state = sessions[user_input.session_id]

    try:
        # Run one step of the graph
        result = onboarding_app.invoke(state)
        sessions[user_input.session_id] = result
        return {"state": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/onboarding/state/{session_id}")
def get_state(session_id: str):
    """
    Fetch current onboarding state.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]


if __name__ == "__main__":
    uvicorn.run("agents.onboarding_agent.onboarding_api:app", host="0.0.0.0", port=8000, reload=True)
