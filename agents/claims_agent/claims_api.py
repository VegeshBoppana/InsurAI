from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from agents.claims_agent.claims_graph import claims_app
from core.db import get_connection

router = APIRouter(prefix="/claims", tags=["Claims"])

# ----------------------------
# Request / Response Models
# ----------------------------
class ClaimRequest(BaseModel):
    user_id: int
    claim_type: str   # "health" or "vehicle"
    document_text: str
    claim_amount: float


class ClaimResponse(BaseModel):
    claim_id: int
    status: str
    reimbursement: float
    message: str

# ----------------------------
# API Route
# ----------------------------
@router.post("/", response_model=ClaimResponse)
def submit_claim(req: ClaimRequest):
    # Initial state for LangGraph
    state = {
        "user_id": req.user_id,
        "claim_type": req.claim_type.lower(),
        "document_text": req.document_text,
        "document_info": None,
        "claim_amount": req.claim_amount,
        "reimbursement": None,
        "otp_verified": False,
        "claim_id": None,
        "error": None
    }

    # Run the LangGraph workflow
    final_state = claims_app.invoke(state)

    if final_state.get("error"):
        raise HTTPException(status_code=400, detail=final_state["error"])

    return ClaimResponse(
        claim_id=final_state["claim_id"],
        status="initiated",
        reimbursement=final_state["reimbursement"],
        message=f"Claim initiated successfully. Approved reimbursement: ₹{final_state['reimbursement']:,}"
    )
