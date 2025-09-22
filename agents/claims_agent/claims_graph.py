from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from datetime import datetime
from core.dial_client import DialClient
from core.db import get_connection
from core.otp_service import send_otp, verify_otp

dial = DialClient()

# ----------------------------
# Claim State
# ----------------------------
class ClaimState(TypedDict):
    insurance_type: str | None          # health or vehicle
    insurance_ref_id: int | None        # id in user_health_insurance or user_vehicle_insurance
    user_id: int | None
    claim_amount: float | None
    claim_reason: str | None
    document_text: str | None
    document_info: str | None
    reimbursement: float | None
    otp_verified: bool
    claim_id: int | None
    claim_number: str | None
    user_name: str | None
    user_email: str | None
    user_phone: str | None
    policy_name: str | None
    policy_coverage: float | None
    policy_premium: float | None
    vehicle_number: str | None
    vehicle_type: str | None
    error: str | None


# ----------------------------
# Node Functions
# ----------------------------
def greet_user(state: ClaimState) -> ClaimState:
    print("👋 Welcome to the Claims Desk!")
    ins_type = input("👉 Is this claim for Health or Vehicle insurance? ").strip().lower()
    if ins_type not in ["health", "vehicle"]:
        state["error"] = "❌ Invalid insurance type."
        return state
    state["insurance_type"] = ins_type
    ins_id = input(f"👉 Please enter your User {ins_type.capitalize()} Insurance ID: ")
    state["insurance_ref_id"] = int(ins_id)
    return state


def verify_insurance(state: ClaimState) -> ClaimState:
    if state.get("error"):
        return state

    conn = get_connection()
    c = conn.cursor()

    if state["insurance_type"] == "health":
        c.execute("""
            SELECT uhi.id, uhi.user_id, uhi.status,
                   p.name, p.coverage_limit, p.premium, p.is_active,
                   u.name, u.email, u.phone
            FROM user_health_insurance uhi
            JOIN policies p ON uhi.policy_id = p.id
            JOIN users u ON uhi.user_id = u.id
            WHERE uhi.id=?
        """, (state["insurance_ref_id"],))
    else:
        c.execute("""
            SELECT uvi.id, uvi.user_id, uvi.status,
                   p.name, p.coverage_limit, p.premium, p.is_active,
                   u.name, u.email, u.phone,
                   uvi.number_plate, uvi.vehicle_type
            FROM user_vehicle_insurance uvi
            JOIN policies p ON uvi.policy_id = p.id
            JOIN users u ON uvi.user_id = u.id
            WHERE uvi.id=?
        """, (state["insurance_ref_id"],))

    row = c.fetchone()
    conn.close()

    if not row:
        state["error"] = "❌ Insurance not found."
        return state

    if state["insurance_type"] == "health":
        _, user_id, status, policy_name, coverage_limit, premium, is_active, name, email, phone = row
        vehicle_number, vehicle_type = None, None
    else:
        _, user_id, status, policy_name, coverage_limit, premium, is_active, name, email, phone, vehicle_number, vehicle_type = row

    if not is_active or status != "active":
        state["error"] = f"❌ This {state['insurance_type']} insurance is inactive."
        return state

    # Save to state
    state.update({
        "user_id": user_id,
        "policy_name": policy_name,
        "policy_coverage": coverage_limit,
        "policy_premium": premium,
        "user_name": name,
        "user_email": email,
        "user_phone": phone,
        "vehicle_number": vehicle_number,
        "vehicle_type": vehicle_type
    })

    # Print summary
    print(f"👤 User: {name} | 📧 {email} | 📱 {phone}")
    print(f"📑 Policy: {policy_name} | 💰 Premium: ₹{premium}/yr | 🛡️ Coverage: ₹{coverage_limit}")
    if vehicle_number:
        print(f"🚘 Vehicle: {vehicle_type} | Plate: {vehicle_number}")

    return state


def show_existing_claims(state: ClaimState) -> ClaimState:
    if state.get("error"):
        return state

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT claim_number, claim_amount, claim_reason, status 
        FROM claims 
        WHERE insurance_type=? AND insurance_ref_id=?
    """, (state["insurance_type"], state["insurance_ref_id"]))
    rows = c.fetchall()
    conn.close()

    if rows:
        print("📑 You already have the following claims:")
        for r in rows:
            print(f"- {r[0]} | Amount: ₹{r[1]} | Reason: {r[2]} | Status: {r[3]}")
        choice = input("👉 Do you want to raise another claim? (yes/no): ").strip().lower()
        if choice != "yes":
            state["error"] = "ℹ️ User chose not to raise another claim."
    else:
        choice = input("👉 You have no existing claims. Do you want to raise one? (yes/no): ").strip().lower()
        if choice != "yes":
            state["error"] = "ℹ️ User chose not to raise a claim."
    return state


def otp_step(state: ClaimState) -> ClaimState:
    if state.get("error"):
        return state

    phone = state.get("user_phone")
    if not phone:
        state["error"] = "❌ User phone not found."
        return state

    send_otp(phone)
    user_input_otp = input("📱 Enter the OTP you received: ")
    state["otp_verified"] = verify_otp(user_input_otp, phone)

    if not state["otp_verified"]:
        state["error"] = "❌ OTP verification failed."
    return state


def collect_claim_details(state: ClaimState) -> ClaimState:
    if state.get("error"):
        return state

    amount = float(input("💰 Enter claim amount: "))
    reason = input("📝 Enter claim reason: ")
    document_text = input("📄 Provide claim document text: ")

    state["claim_amount"] = amount
    state["claim_reason"] = reason
    state["document_text"] = document_text
    return state


def validate_document(state: ClaimState) -> ClaimState:
    if state.get("error"):
        return state

    doc_text = state.get("document_text", "")
    claim_type = state.get("insurance_type")

    result = dial.validate_claim_document(claim_type, doc_text)
    if result.startswith("YES"):
        state["document_info"] = result.split("|", 1)[-1].strip()
    else:
        state["error"] = "❌ Invalid document."
    return state


def save_claim(state: ClaimState) -> ClaimState:
    if state.get("error"):
        return state

    conn = get_connection()
    c = conn.cursor()
    try:
        # Calculate reimbursement
        coverage_limit = state["policy_coverage"]
        reimbursement = min(state["claim_amount"], coverage_limit)
        state["reimbursement"] = reimbursement

        # Insert claim
        c.execute("""
            INSERT INTO claims (user_id, insurance_type, insurance_ref_id, claim_reason, document_text, document_info, claim_amount, reimbursement, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'initiated')
        """, (
            state["user_id"],
            state["insurance_type"],
            state["insurance_ref_id"],
            state["claim_reason"],
            state["document_text"],
            state["document_info"],
            state["claim_amount"],
            reimbursement
        ))
        conn.commit()
        claim_id = c.lastrowid

        # Generate claim number
        year = datetime.now().year
        claim_number = f"CLM-{year}-{claim_id:05d}"
        c.execute("UPDATE claims SET claim_number=? WHERE id=?", (claim_number, claim_id))
        conn.commit()

        state["claim_id"] = claim_id
        state["claim_number"] = claim_number

    except Exception as e:
        state["error"] = f"❌ Claim failed: {str(e)}"
    finally:
        conn.close()

    return state


def confirm_claim(state: ClaimState) -> ClaimState:
    if state.get("error"):
        print(state["error"])
    else:
        print(
            f"✅ Claim {state['claim_number']} initiated successfully for {state['user_name']}.\n"
            f"💰 Amount: ₹{state['claim_amount']} | Reason: {state['claim_reason']} | Status: Initiated\n"
            f"Approved Reimbursement: ₹{state['reimbursement']:,}"
        )
        if state["insurance_type"] == "vehicle":
            print(f"🚘 Vehicle: {state['vehicle_type']} | Plate: {state['vehicle_number']}")
    return state


# ----------------------------
# Build LangGraph
# ----------------------------
workflow = StateGraph(ClaimState)

workflow.add_node("Greet", greet_user)
workflow.add_node("VerifyInsurance", verify_insurance)
workflow.add_node("ShowClaims", show_existing_claims)
workflow.add_node("OTP", otp_step)
workflow.add_node("CollectDetails", collect_claim_details)
workflow.add_node("ValidateDoc", validate_document)
workflow.add_node("SaveClaim", save_claim)
workflow.add_node("Confirm", confirm_claim)

workflow.add_edge(START, "Greet")
workflow.add_edge("Greet", "VerifyInsurance")
workflow.add_edge("VerifyInsurance", "ShowClaims")
workflow.add_edge("ShowClaims", "OTP")
workflow.add_edge("OTP", "CollectDetails")
workflow.add_edge("CollectDetails", "ValidateDoc")
workflow.add_edge("ValidateDoc", "SaveClaim")
workflow.add_edge("SaveClaim", "Confirm")
workflow.add_edge("Confirm", END)

claims_app = workflow.compile()
