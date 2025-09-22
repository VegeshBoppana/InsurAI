from fastapi import FastAPI
from agents.claims_agent.claims_api import router as claims_router

app = FastAPI(title="Insurance Agents API")

# Register routers
app.include_router(claims_router)

@app.get("/")
def root():
    return {"message": "Insurance Agents API is running 🚀"}
