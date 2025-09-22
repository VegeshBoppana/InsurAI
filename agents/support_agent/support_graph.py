from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from core.dial_client import DialClient
import json, time, re

dial = DialClient()

class SupportState(TypedDict, total=False):
    name: str
    current_topic: str
    conversation: list
    user_query: str
    satisfaction: bool
    needs_human: bool
    session_complete: bool


# ----------------------------
# Knowledge Base
# ----------------------------
COMPANY_INFO = {
    "about": """InsurAI is your friendly neighborhood insurance company that actually gets it. We've been helping families and individuals protect what matters most to them for over a decade. 
    
    What makes us different? We use smart technology to make insurance simple and affordable, but we never forget there's a real person behind every policy. Our team is here 24/7 because life doesn't happen on a schedule.
    
    We're licensed across India and have helped over 2 million customers find the right coverage. Most importantly, when you need us most - during a claim - we're known for being fast, fair, and hassle-free.""",
    
    "mission": "We believe everyone deserves great insurance without the headaches. Our mission is to make insurance so simple and trustworthy that you actually feel good about having it.",
    
    "benefits": [
        "24/7 customer support - real people, not bots",
        "Super fast claim processing - most claims settled within 48 hours", 
        "No hidden fees or surprises - what you see is what you pay",
        "Easy online policy management through our app",
        "Cashless service network across 10,000+ hospitals and garages",
        "Free annual health checkups for health insurance members",
        "Roadside assistance anywhere in India for vehicle insurance"
    ]
}

INSURANCE_EDUCATION = {
    "health_insurance": {
        "what_is": "Health insurance is basically your safety net for medical expenses. Think of it like this - you pay a small amount every month, and if you ever get sick or injured, we take care of the big hospital bills. It covers everything from doctor visits to surgeries to medicines.",
        
        "why_need": "Here's the thing - medical costs have gone crazy expensive. A simple surgery can cost lakhs. Without insurance, one medical emergency could wipe out your savings. With insurance, you get treatment at the best hospitals without worrying about money.",
        
        "what_covers": "Most health plans cover hospitalization, surgeries, medicines, doctor consultations, diagnostic tests, and even ambulance costs. Some also include dental care, maternity benefits, and mental health support.",
        
        "types": "Family plans cover your whole family under one policy - usually cheaper. Individual plans are just for you. Senior citizen plans are specially designed for older folks with their specific health needs."
    },
    
    "vehicle_insurance": {
        "what_is": "Vehicle insurance protects you financially if something happens to your car or bike. It's actually required by law in India - you can't legally drive without at least basic coverage.",
        
        "why_need": "Accidents happen, theft happens, natural disasters happen. Without insurance, you'd have to pay for repairs, replacement, or worse - if you hurt someone else, you could face huge legal costs. Insurance handles all of that.",
        
        "what_covers": "Third-party insurance (the minimum legal requirement) covers damage you cause to others. Comprehensive insurance also covers damage to your own vehicle from accidents, theft, fire, floods, etc.",
        
        "types": "Third-party is the bare minimum - covers others but not your vehicle. Comprehensive covers everything including your own car. Zero depreciation means you get full value for parts, not reduced for wear and tear."
    }
}


# ----------------------------
# Helper Functions
# ----------------------------
def llm_classify_query(state: SupportState, user_query: str) -> str:
    """Classify what the user is asking about"""
    prompt = f"""
User query: "{user_query}"
Previous conversation: {json.dumps(state.get("conversation", []), indent=2)}

Classify this query into one of these categories:
- health_insurance (questions about health insurance)
- vehicle_insurance (questions about vehicle/car/bike insurance)  
- company_info (questions about InsurAI company, services, benefits)
- claims (questions about claim process)
- general_help (general questions, greetings, unclear queries)
- satisfied (user seems satisfied/wants to end conversation)

Reply with just the category name.
"""
    
    try:
        resp = dial.chat([
            {"role": "system", "content": "You are a support query classifier."},
            {"role": "user", "content": prompt}
        ])
        category = resp.strip().lower()
        valid_categories = ["health_insurance", "vehicle_insurance", "company_info", "claims", "general_help", "satisfied"]
        return category if category in valid_categories else "general_help"
    except:
        return "general_help"


def llm_generate_response(state: SupportState, user_query: str, category: str) -> str:
    """Generate human-like responses based on query category"""
    
    if category == "company_info":
        context = f"""
        Company Info: {COMPANY_INFO['about']}
        Mission: {COMPANY_INFO['mission']}
        Key Benefits: {', '.join(COMPANY_INFO['benefits'])}
        """
    elif category == "health_insurance":
        context = f"""
        Health Insurance Info:
        What it is: {INSURANCE_EDUCATION['health_insurance']['what_is']}
        Why you need it: {INSURANCE_EDUCATION['health_insurance']['why_need']}
        What it covers: {INSURANCE_EDUCATION['health_insurance']['what_covers']}
        Types: {INSURANCE_EDUCATION['health_insurance']['types']}
        """
    elif category == "vehicle_insurance":
        context = f"""
        Vehicle Insurance Info:
        What it is: {INSURANCE_EDUCATION['vehicle_insurance']['what_is']}
        Why you need it: {INSURANCE_EDUCATION['vehicle_insurance']['why_need']}
        What it covers: {INSURANCE_EDUCATION['vehicle_insurance']['what_covers']}
        Types: {INSURANCE_EDUCATION['vehicle_insurance']['types']}
        """
    else:
        context = "General insurance and company support information available."
    
    conversation_history = json.dumps(state.get("conversation", []), indent=2)
    
    prompt = f"""
You are Maya, a friendly support agent at InsurAI. You're talking to {state.get('name', 'someone')} who needs help understanding insurance.

Talk like a real person - warm, knowledgeable but not pushy. Use:
- Natural conversation style with contractions (I'm, you're, that's, we've)
- Casual phrases (You know what, Actually, Here's the thing)
- Personal touches (I help people with this all the time, Most of our customers)
- Simple, clear explanations without jargon

AVOID:
- Being overly enthusiastic or salesy
- Corporate buzzwords
- Long paragraphs - keep responses conversational length
- Saying "customer" - say "you" instead

Context about query type "{category}":
{context}

Previous conversation:
{conversation_history}

User just asked: "{user_query}"

Give a helpful, natural response. If they're asking about something specific, explain it simply. If it's a general question, guide them to what they might want to know.
"""
    
    try:
        response = dial.chat([
            {"role": "system", "content": "You are Maya, a friendly and knowledgeable insurance support agent."},
            {"role": "user", "content": prompt}
        ])
        return response.strip()
    except:
        return "I'm here to help you understand insurance better. What would you like to know about?"


# ----------------------------
# Workflow Nodes
# ----------------------------
def welcome_user(state: SupportState) -> SupportState:
    """Welcome the user and get their name"""
    print("Hi there! I'm Maya from InsurAI support. I'm here to help you understand insurance and answer any questions you have.")
    
    name_input = input("What should I call you? ").strip()
    if name_input:
        state["name"] = name_input
        print(f"Nice to meet you, {name_input}!")
    else:
        state["name"] = "friend"
        print("No worries!")
    
    state["conversation"] = []
    return state


def get_user_query(state: SupportState) -> SupportState:
    """Get what the user wants to know about"""
    print("\nSo what can I help you with today? You can ask me about:")
    print("- Health insurance - what it is, why you need it")
    print("- Vehicle insurance - car, bike coverage")  
    print("- About InsurAI - our company and services")
    print("- Or anything else insurance-related!")
    
    query = input("\nWhat's on your mind? ").strip()
    state["user_query"] = query
    state["conversation"].append({"role": "user", "content": query, "timestamp": time.time()})
    
    return state


def process_query(state: SupportState) -> SupportState:
    """Process the user's query and provide helpful information"""
    user_query = state.get("user_query", "")
    
    # Classify the query
    category = llm_classify_query(state, user_query)
    state["current_topic"] = category
    
    # Generate response based on category
    if category == "satisfied":
        print("Glad I could help! Is there anything else you'd like to know?")
        state["satisfaction"] = True
    else:
        response = llm_generate_response(state, user_query, category)
        print(f"\n{response}")
        
        state["conversation"].append({
            "role": "assistant", 
            "content": response,
            "category": category,
            "timestamp": time.time()
        })
    
    return state


def handle_followup(state: SupportState) -> SupportState:
    """Handle follow-up questions and check if user needs more help"""
    while True:
        followup = input("\nAnything else you'd like to know? (or say 'thanks' if you're all set): ").strip().lower()
        
        if not followup or followup in ["thanks", "thank you", "no", "nope", "i'm good", "all good", "that's it"]:
            state["satisfaction"] = True
            print(f"You're welcome, {state.get('name')}! Feel free to reach out anytime if you have more questions.")
            print("Have a great day!")
            break
        
        # Process the follow-up question
        state["user_query"] = followup
        state["conversation"].append({"role": "user", "content": followup, "timestamp": time.time()})
        
        category = llm_classify_query(state, followup)
        response = llm_generate_response(state, followup, category)
        print(f"\n{response}")
        
        state["conversation"].append({
            "role": "assistant",
            "content": response,
            "category": category, 
            "timestamp": time.time()
        })
        
        # Check if this seems like a complex issue that needs human help
        if "claim" in followup.lower() and "problem" in followup.lower():
            print("\nActually, for specific claim issues, let me connect you with one of our claims specialists who can look into your account directly.")
            state["needs_human"] = True
            break
    
    state["session_complete"] = True
    return state


def end_session(state: SupportState) -> SupportState:
    """End the support session"""
    if state.get("needs_human"):
        print("I'll have someone from our team call you within the next hour to help with your specific situation.")
    
    print("\nThanks for choosing InsurAI! Remember, we're here 24/7 if you need anything.")
    return state


# ----------------------------
# Graph Setup
# ----------------------------
workflow = StateGraph(SupportState)

# Add nodes
workflow.add_node("Welcome", welcome_user)
workflow.add_node("GetQuery", get_user_query) 
workflow.add_node("ProcessQuery", process_query)
workflow.add_node("HandleFollowup", handle_followup)
workflow.add_node("EndSession", end_session)

# Add edges
workflow.add_edge(START, "Welcome")
workflow.add_edge("Welcome", "GetQuery")
workflow.add_edge("GetQuery", "ProcessQuery")
workflow.add_edge("ProcessQuery", "HandleFollowup")

# Conditional edge from HandleFollowup
workflow.add_conditional_edges(
    "HandleFollowup",
    lambda state: "EndSession" if state.get("session_complete") else "HandleFollowup",
    {"EndSession": "EndSession", "HandleFollowup": "HandleFollowup"}
)

workflow.add_edge("EndSession", END)

# Compile the workflow
support_app = workflow.compile()


# ----------------------------
# Main Function to Run Support
# ----------------------------
def run_support():
    """Run the support agent"""
    print("=" * 50)
    print("InsurAI Support - We're here to help!")
    print("=" * 50)
    
    try:
        initial_state = SupportState()
        final_state = support_app.invoke(initial_state)
        return final_state
    except KeyboardInterrupt:
        print("\n\nThanks for visiting InsurAI support. Have a great day!")
    except Exception as e:
        print(f"\nSorry, something went wrong on our end. Please try again or call our support line.")
        print(f"Error: {e}")


if __name__ == "__main__":
    run_support()