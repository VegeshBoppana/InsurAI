# main.py
from fastapi import FastAPI
import uvicorn

# Import routers
from agents.support_agent.support_api import router as support_router
from agents.claims_agent.claims_api import router as claims_router
from agents.onboarding_agent.onboarding_api import app as onboarding_app  # already a FastAPI app

# Main app
app = FastAPI(
    title="Insurance Agents API",
    version="1.0",
    description="Unified API for Support, Onboarding, and Claims agents"
)

# Register routers
app.include_router(support_router, prefix="/support", tags=["Support"])
app.include_router(claims_router, prefix="/claims", tags=["Claims"])

# Mount onboarding as a sub-app since it's already a FastAPI app
app.mount("/onboarding", onboarding_app)

@app.get("/")
def root():
    return {"message": "Insurance Agents API is running 🚀. Endpoints: /support, /claims, /onboarding"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
