from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from core.dial_client import DialClient
from core.email_service import send_policy_email, generate_policy_pdf
import json, time, re, os

dial = DialClient()
POLICY_FILE = "policies.json"


class OnboardingState(TypedDict, total=False):
    insurance_choice: str
    details: dict
    premium: float
    coverage: float
    benefits: str
    confirmed: bool
    discount_applied: bool
    email: str
    name: str
    phone: str
    error: str
    conversation: list
    reconsider: bool


# ----------------------------
# Helpers
# ----------------------------
def parse_number(text: str, default: int = 0) -> int:
    if not text:
        return default
    text = text.lower().replace(",", "").strip()
    match = re.match(r"(\d+)(k)?", text)
    if match:
        num = int(match.group(1))
        if match.group(2):
            num *= 1000
        return num
    try:
        return int(text)
    except:
        return default


def llm_classify_intent(state: OnboardingState, user_msg: str) -> str:
    prompt = f"""
Conversation so far:
{json.dumps(state.get("conversation", []), indent=2)}

Current policy:
Premium INR {int(state.get("premium",0))}, Coverage INR {state.get("coverage",0)}, Benefits: {state.get("benefits","")}

User just said: "{user_msg}"

Classify the user's intent into one of:
- negotiate
- benefits
- confirm
- reject
- reconsider
- other
Reply with just one label.
"""
    try:
        resp = dial.chat([
            {"role": "system", "content": "You are an insurance assistant that classifies user intent."},
            {"role": "user", "content": prompt}
        ])
        intent = resp.strip().lower()
        return intent if intent in ["negotiate", "benefits", "confirm", "reject", "reconsider", "other"] else "other"
    except:
        return "other"


def llm_human_reply(state: OnboardingState, user_msg: str) -> str:
    policy_context = f"Premium INR {int(state['premium'])}, Coverage INR {state['coverage']}, Benefits: {state['benefits']}"
    conversation = json.dumps(state.get("conversation", []), indent=2)

    prompt = f"""
You are a friendly, experienced insurance agent named Sarah talking to {state.get('name','the customer')} over the phone.
Talk like a real person - casual, warm, and genuine. Use natural speech patterns with:
- Contractions (I'll, you're, we've, that's)
- Casual phrases (Oh absolutely, You know what, I hear you)
- Natural hesitations (Well, I mean, Actually)
- Personal touches (I've helped tons of customers with this)

AVOID:
- Corporate speak or formal language
- Bullet points or structured responses
- Being overly enthusiastic or salesy
- Using "customer" - say "you" instead

Current policy:
{policy_context}

Conversation so far:
{conversation}

Customer just said: "{user_msg}"

Respond naturally like you're having a real conversation. Keep it short and conversational - 1-2 sentences max.
"""
    try:
        reply = dial.chat([
            {"role": "system", "content": "You are Sarah, a friendly insurance agent having a natural phone conversation."},
            {"role": "user", "content": prompt}
        ])
        return reply.strip()
    except:
        return "Hmm, let me think about that. This plan covers the main things - accidents, theft, roadside help. What do you think?"


def llm_choose_plan(state: OnboardingState, user_request: str):
    prompt = f"""
You are an experienced insurance agent. You have 3 plans:

1. Basic — cheaper premium, basic coverage
2. Standard — good balance, most popular 
3. Premium — higher premium, comprehensive coverage with extras

Customer said: "{user_request}"

Pick the most suitable plan based on their needs.
Reply in JSON like:
{{"plan":"2","reason":"Sounds like they want good coverage without breaking the bank"}}
"""
    try:
        resp = dial.chat([
            {"role": "system", "content": "You are an insurance agent helping pick the right plan."},
            {"role": "user", "content": prompt}
        ])
        data = json.loads(resp)
        if "plan" in data and data["plan"] in {"1", "2", "3"}:
            return data
    except:
        pass
    return None


def save_policy_json(state: OnboardingState):
    record = {
        "name": state.get("name"),
        "phone": state.get("phone"),
        "email": state.get("email"),
        "plan": state.get("insurance_choice"),
        "premium": int(state.get("premium", 0)),
        "coverage": state.get("coverage"),
        "benefits": state.get("benefits"),
        "timestamp": int(time.time())
    }
    try:
        if os.path.exists(POLICY_FILE):
            with open(POLICY_FILE, "r") as f:
                data = json.load(f)
        else:
            data = []
        data.append(record)
        with open(POLICY_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Policy saved to {POLICY_FILE}")
    except Exception as e:
        print("Failed to save policy JSON:", e)


# ----------------------------
# Nodes
# ----------------------------
def collect_user_info(state: OnboardingState) -> OnboardingState:
    print("Hi there! I'm Sarah from InsurAI. I'm here to help you find the right insurance today.")
    state["name"] = input("Let's start with your name - what should I call you? ").strip()
    state["phone"] = input("And can I get your mobile number? ").strip()
    state["conversation"] = []
    return state


def ask_type(state: OnboardingState) -> OnboardingState:
    print(f"\nNice to meet you, {state['name']}! So what brings you here today - looking for health insurance or something for your vehicle?")
    choice = input("> ").strip()
    state["insurance_choice"] = choice
    state["conversation"].append({"role": "user", "content": choice})
    return state


def vehicle_tool(state: OnboardingState) -> OnboardingState:
    print("\nAlright, let me get some details about your ride.")
    name = input("What kind of vehicle are we talking about? ").strip()
    kms = input("How many kilometers has it done so far? ").strip()
    age = input("And how old is it - in years? ").strip()
    cc = input("What's the engine size? ").strip()

    kms_val = parse_number(kms, 0)
    age_val = parse_number(age, 0)
    cc_val = parse_number(cc, 0)

    state["details"] = {"name": name, "kms": kms_val, "age": age_val, "cc": cc_val}

    base_premium = 5000 + age_val * 200 + (kms_val // 10000) * 300
    state["premium"] = float(base_premium)
    state["coverage"] = 200000
    state["benefits"] = "Accident cover, theft protection, roadside assistance"
    return state


def health_tool(state: OnboardingState) -> OnboardingState:
    print("\nGreat choice on the health insurance. Let me understand your family situation.")
    members = parse_number(input("How many people do you want covered including yourself? ").strip(), 1)
    avg_age = parse_number(input("What's the average age of everyone? ").strip(), 30)
    state["details"] = {"members": members, "age": avg_age}
    base_premium = 8000 + members * 2000 + (avg_age // 10) * 1000
    state["premium"] = float(base_premium)
    state["coverage"] = 500000
    state["benefits"] = "Hospitalization cover, critical illness cover, free annual health check-up"
    return state


def plan_options(state: OnboardingState) -> OnboardingState:
    state["reconsider"] = False
    base_premium = state["premium"]
    base_coverage = state["coverage"]
    base_benefits = state["benefits"]

    plans = {
        "1": {"name": "Basic", "premium": int(base_premium * 0.8), "coverage": int(base_coverage * 0.8), "benefits": base_benefits},
        "2": {"name": "Standard", "premium": int(base_premium), "coverage": base_coverage, "benefits": base_benefits},
        "3": {"name": "Premium", "premium": int(base_premium * 1.2), "coverage": int(base_coverage * 1.5), "benefits": base_benefits + ", legal protection cover"}
    }

    print(f"\nOkay {state['name']}, based on what you've told me, I've got three options for you:")
    print(f"The Basic plan is {plans['1']['premium']} rupees - covers the essentials, keeps costs down.")
    print(f"Standard is {plans['2']['premium']} - that's what most people go with, good balance.")
    print(f"And Premium is {plans['3']['premium']} - gives you everything plus legal cover too.")

    user_choice = input("What feels right to you? You can just say 1, 2, 3 or tell me what you're thinking: ").strip()

    if user_choice in plans:
        state.update(plans[user_choice])
        return state

    for k, p in plans.items():
        if p["name"].lower() in user_choice.lower():
            state.update(plans[k])
            return state

    decision = llm_choose_plan(state, user_choice)
    if decision and decision["plan"] in plans:
        print(f"You know what, from what you're saying, I think the {plans[decision['plan']]['name']} plan makes sense.")
        print(f"{decision['reason']}")
        state.update(plans[decision["plan"]])
        return state

    print("Sorry, I didn't quite catch that. Let me ask again.")
    return plan_options(state)


def policy_present(state: OnboardingState) -> OnboardingState:
    print(f"\nPerfect! So here's what we've got for you, {state['name']}:")
    print(f"You'll pay {int(state['premium'])} rupees for this")
    print(f"Coverage up to {state['coverage']} rupees") 
    print(f"And you get: {state['benefits']}")
    return state


def negotiate_confirm(state: OnboardingState) -> OnboardingState:
    while True:
        user_msg = input("\nWhat do you think? ").strip()
        state["conversation"].append({"role": "user", "content": user_msg, "ts": int(time.time())})
        intent = llm_classify_intent(state, user_msg)

        if intent == "negotiate":
            if state.get("discount_applied"):
                print("I hear you on the price, but honestly this is already our best rate. You're getting solid coverage and we're really good with claims.")
            else:
                new_premium = round(state["premium"] * 0.95, 2)
                state["premium"] = new_premium
                state["discount_applied"] = True
                print(f"You know what, let me see what I can do... I can bring it down to {int(new_premium)} rupees. That's really the best I can offer.")
            continue

        elif intent == "benefits":
            print(llm_human_reply(state, user_msg))
            continue

        elif intent == "confirm":
            state["confirmed"] = True
            print(f"Excellent! I'm so glad we found something that works for you, {state['name']}. Let me get this sorted out.")
            return state

        elif intent == "reject":
            state["confirmed"] = False
            state["error"] = "User rejected the policy."
            print("No worries at all. If things change or you want to chat about options later, just give us a call, okay?")
            return state

        elif intent == "reconsider":
            decision = llm_choose_plan(state, user_msg)
            if decision:
                print(f"Actually, let me show you the {plans[decision['plan']]['name']} plan instead - {decision['reason']}.")
                state["reconsider"] = True
                return state
            else:
                state["reconsider"] = True
                print("Sure thing, let's look at the other options again.")
                return state

        else:
            print(llm_human_reply(state, user_msg))
            continue


def email_tool(state: OnboardingState) -> OnboardingState:
    if not state.get("email"):
        state["email"] = input("Great! I'll need your email to send over the policy documents: ").strip()

    pdf_path = generate_policy_pdf(
        user_name=state.get("name", "Customer"),
        policy_name=state.get("insurance_choice", "Insurance"),
        premium=state.get("premium", 0),
        coverage=state.get("coverage", 0),
        benefits=state.get("benefits", ""),
        insurance_type=state.get("insurance_choice", "general"),
        filename="policy.pdf"
    )

    subject = f"Your {state.get('insurance_choice','Insurance')} Policy - All Set!"
    body = f"""Hi {state.get('name')},

Great talking with you today! Thanks for trusting us with your insurance.

Here's what we set up for you:
- You'll pay INR {int(state.get('premium',0))} 
- Coverage up to INR {state.get('coverage')}
- Includes: {state.get('benefits')}

I've attached your official policy document. Keep it handy!

If you have any questions at all, just give me a call.

Best,  
Sarah
InsurAI
"""

    send_policy_email(state["email"], subject, body, pdf_path)
    save_policy_json(state)
    print(f"Perfect! I've sent everything to {state['email']}. You should get it in a couple minutes.")
    print("Thanks for choosing us today! Take care.")
    return state


# ----------------------------
# Graph
# ----------------------------
workflow = StateGraph(OnboardingState)
workflow.add_node("UserInfo", collect_user_info)
workflow.add_node("AskType", ask_type)
workflow.add_node("VehicleTool", vehicle_tool)
workflow.add_node("HealthTool", health_tool)
workflow.add_node("PlanOptions", plan_options)
workflow.add_node("PolicyPresent", policy_present)
workflow.add_node("NegotiateConfirm", negotiate_confirm)
workflow.add_node("EmailTool", email_tool)

workflow.add_edge(START, "UserInfo")
workflow.add_edge("UserInfo", "AskType")
workflow.add_conditional_edges(
    "AskType",
    lambda s: "VehicleTool" if "vehicle" in s.get("insurance_choice", "").lower() or "car" in s.get("insurance_choice", "").lower() else "HealthTool",
    {"VehicleTool": "VehicleTool", "HealthTool": "HealthTool"}
)
workflow.add_edge("VehicleTool", "PlanOptions")
workflow.add_edge("HealthTool", "PlanOptions")
workflow.add_edge("PlanOptions", "PolicyPresent")
workflow.add_edge("PolicyPresent", "NegotiateConfirm")

workflow.add_conditional_edges(
    "NegotiateConfirm",
    lambda s: (
        "EmailTool" if s.get("confirmed")
        else ("PlanOptions" if s.get("reconsider")
              else ("END" if s.get("error") else "NegotiateConfirm"))
    ),
    {"EmailTool": "EmailTool", "PlanOptions": "PlanOptions", "NegotiateConfirm": "NegotiateConfirm", "END": END}
)

workflow.add_edge("EmailTool", END)

onboarding_app = workflow.compile()