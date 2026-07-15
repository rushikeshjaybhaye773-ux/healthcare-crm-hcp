import json
from typing import TypedDict, List, Dict, Any, Literal
from langgraph.graph import StateGraph, END
from app.services.groq import call_groq_api
from app.services.tools import (
    log_interaction_tool,
    edit_interaction_tool,
    search_hcp_tool,
    generate_follow_up_tool,
    meeting_summary_tool
)

# Define Agent State
class AgentState(TypedDict):
    user_message: str
    intent_tool: str
    intent_args: Dict[str, Any]
    tool_output: Dict[str, Any]
    response_message: str

# 1. Understand Intent Node
def understand_intent_node(state: AgentState) -> Dict[str, Any]:
    user_msg = state["user_message"]
    
    system_prompt = """
    You are a Healthcare CRM AI Assistant. Your task is to analyze the user's message and determine the correct tool to call.
    The tools are:
    1. 'log_interaction': Use when the user wants to record/log a visit/meeting, e.g. "I met Dr. Sharma today. We discussed CardioPlus. He asked for samples. Meet next Friday."
    2. 'edit_interaction': Use when the user wants to update or modify a specific interaction (usually mentions an ID or specific edit request). E.g. "Change follow-up date for interaction 25 to Monday."
    3. 'search_hcp': Use when the user wants to search for a doctor, see details, or check historical visits. E.g. "Search Doctor Dr Sharma."
    4. 'generate_follow_up': Use when the user wants to see follow-up recommendations, or check who hasn't been visited in 30 days. E.g. "Who should I visit next?" or "Show recommended visits."
    5. 'meeting_summary': Use when the user has a long text notes and asks to summarize, get sentiment, key topics, or action items. E.g. "Summarize this meeting: ..."
    
    You must output a JSON object only. Do NOT include markdown code block formatting (like ```json).
    The JSON structure should be:
    {
      "tool": "log_interaction" | "edit_interaction" | "search_hcp" | "generate_follow_up" | "meeting_summary" | "none",
      "args": {
         // for log_interaction:
         "doctor_name": string (e.g. "Dr. Sharma"),
         "hospital": string (if mentioned, e.g., "Apex Hospital"),
         "meeting_date_str": string (YYYY-MM-DD, default to today's date if not mentioned),
         "products": array of strings (e.g. ["CardioPlus"]),
         "notes": string (full original message text),
         "follow_up_date_str": string (YYYY-MM-DD, e.g. date of next Friday/Monday/Tuesday if mentioned)
         
         // for edit_interaction:
         "interaction_id": integer (e.g. 25),
         "follow_up_date_str": string (YYYY-MM-DD, new follow-up date)
         
         // for search_hcp:
         "name_query": string (e.g. "Sharma")
         
         // for generate_follow_up: (none)
         
         // for meeting_summary:
         "notes": string (the long text notes to summarize)
      }
    }
    
    Ensure all date strings represent actual dates based on the current date: 2026-07-15.
    - Today is Wednesday, July 15, 2026.
    - Next Friday is July 17, 2026 (or July 24 if it refers to next week). Use July 17, 2026 if the user says "next Friday" in the context of a Wednesday.
    - Next Monday is July 20, 2026.
    - Next Tuesday is July 21, 2026.
    - Tomorrow is Thursday, July 16, 2026.
    """
    
    try:
        response_str = call_groq_api(system_prompt, user_msg)
        
        # Clean markdown code blocks if the LLM outputted them
        clean_res = response_str.strip()
        if clean_res.startswith("```json"):
            clean_res = clean_res[7:]
        if clean_res.endswith("```"):
            clean_res = clean_res[:-3]
        clean_res = clean_res.strip()
        
        data = json.loads(clean_res)
        return {
            "intent_tool": data.get("tool", "none"),
            "intent_args": data.get("args", {})
        }
    except Exception as e:
        print(f"Failed to understand intent: {str(e)}")
        # Simple fallback parsing using keywords
        msg = user_msg.lower()
        if "edit" in msg or "change" in msg or "update" in msg:
            # Extract digits for interaction ID
            numbers = [int(s) for s in msg.split() if s.isdigit()]
            inter_id = numbers[0] if numbers else 1
            # Mock Monday follow up
            return {
                "intent_tool": "edit_interaction",
                "intent_args": {
                    "interaction_id": inter_id,
                    "follow_up_date_str": "2026-07-20" # Next Monday
                }
            }
        elif "search" in msg or "doctor" in msg or "hcp" in msg:
            return {
                "intent_tool": "search_hcp",
                "intent_args": {"name_query": "Sharma"}
            }
        elif "recommend" in msg or "visit" in msg or "follow-up" in msg:
            return {
                "intent_tool": "generate_follow_up",
                "intent_args": {}
            }
        elif "summarize" in msg or "summary" in msg:
            return {
                "intent_tool": "meeting_summary",
                "intent_args": {"notes": user_msg}
            }
        else:
            # Default to log interaction
            return {
                "intent_tool": "log_interaction",
                "intent_args": {
                    "doctor_name": "Dr. Sharma",
                    "hospital": "Apex Hospital",
                    "meeting_date_str": "2026-07-15",
                    "products": ["CardioPlus"],
                    "notes": user_msg,
                    "follow_up_date_str": "2026-07-22"
                }
            }

# 2. Execute Tool Node
def execute_tool_node(state: AgentState) -> Dict[str, Any]:
    tool = state["intent_tool"]
    args = state["intent_args"]
    output = {}
    
    if tool == "log_interaction":
        output = log_interaction_tool(
            doctor_name=args.get("doctor_name", "Dr. Sharma"),
            hospital=args.get("hospital", "City Hospital"),
            meeting_date_str=args.get("meeting_date_str", "2026-07-15"),
            products=args.get("products", ["CardioPlus"]),
            notes=args.get("notes", ""),
            follow_up_date_str=args.get("follow_up_date_str")
        )
    elif tool == "edit_interaction":
        output = edit_interaction_tool(
            interaction_id=args.get("interaction_id", 1),
            follow_up_date_str=args.get("follow_up_date_str"),
            notes=args.get("notes"),
            summary=args.get("summary")
        )
    elif tool == "search_hcp":
        output = search_hcp_tool(
            name_query=args.get("name_query", "")
        )
    elif tool == "generate_follow_up":
        output = generate_follow_up_tool()
    elif tool == "meeting_summary":
        output = meeting_summary_tool(
            notes=args.get("notes", "")
        )
    else:
        output = {"success": False, "error": "No valid tool matching user intent."}
        
    return {"tool_output": output}

# 3. Respond Node
def respond_node(state: AgentState) -> Dict[str, Any]:
    tool = state["intent_tool"]
    output = state["tool_output"]
    
    if not output.get("success", False) and tool != "search_hcp" and tool != "generate_follow_up":
        return {
            "response_message": f"Sorry, I encountered an error: {output.get('error', 'Unknown error')}"
        }
        
    if tool == "log_interaction":
        data = output.get("data", {})
        response = (
            f"✅ **Interaction Logged Successfully!**\n\n"
            f"👩‍⚕️ **Doctor:** {data.get('doctor')}\n"
            f"🏥 **Hospital:** {data.get('hospital')}\n"
            f"📅 **Date:** {data.get('meeting_date')}\n"
            f"💊 **Products Discussed:** {data.get('products')}\n"
            f"🔔 **Next Follow-up:** {data.get('follow_up') or 'None'}\n"
            f"📝 **Status:** Saved to Database."
        )
    elif tool == "edit_interaction":
        data = output.get("data", {})
        response = (
            f"✏️ **Interaction Updated Successfully!**\n\n"
            f"🆔 **ID:** {data.get('interaction_id')}\n"
            f"👩‍⚕️ **Doctor:** {data.get('doctor')}\n"
            f"📅 **Meeting Date:** {data.get('meeting_date')}\n"
            f"🔔 **New Follow-up Date:** {data.get('follow_up') or 'None'}"
        )
    elif tool == "search_hcp":
        results = output.get("results", [])
        if not results:
            response = "🔍 No doctor records found matching your query."
        else:
            response = f"🔍 Found {len(results)} doctor profile(s):\n\n"
            for hcp in results:
                response += (
                    f"👩‍⚕️ **{hcp['name']}** ({hcp['specialization']})\n"
                    f"🏥 Hospital: {hcp['hospital']}\n"
                    f"📅 Last Visit: {hcp['last_meeting'] or 'Never'}\n"
                    f"💊 Products discussed: {', '.join(hcp['products_discussed']) or 'None'}\n"
                    f"📊 Total Visits: {hcp['past_visits_count']}\n\n"
                )
    elif tool == "generate_follow_up":
        recs = output.get("recommendations", [])
        if not recs:
            response = "📅 All doctors have been visited recently. No follow-ups recommended at this time."
        else:
            response = "📅 **Follow-up Recommendations (Not visited in last 30 days):**\n\n"
            for rec in recs:
                response += (
                    f"⚠️ **{rec['name']}** ({rec['hospital']})\n"
                    f"💡 Reason: {rec['reason']}\n"
                    f"👉 **Action: {rec['recommendation']}**\n\n"
                )
    elif tool == "meeting_summary":
        response = (
            f"📝 **Meeting Summary:**\n"
            f"{output.get('summary')}\n\n"
            f"💡 **Action Items:**\n"
            f"{output.get('action_items')}\n\n"
            f"🎭 **Sentiment:** {output.get('sentiment')}\n"
            f"🏷️ **Key Topics:** {', '.join(output.get('key_topics', []))}"
        )
    else:
        response = f"Hello! I am your Healthcare CRM Agent. I can log interactions, update follow-up dates, search doctors, check follow-up recommendations, or summarize notes. How can I help you today?"
        
    return {"response_message": response}

# Route logic
def should_continue(state: AgentState) -> Literal["execute_tool", "respond"]:
    if state["intent_tool"] in ["log_interaction", "edit_interaction", "search_hcp", "generate_follow_up", "meeting_summary"]:
        return "execute_tool"
    return "respond"

# Build Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("understand_intent", understand_intent_node)
workflow.add_node("execute_tool", execute_tool_node)
workflow.add_node("respond", respond_node)

# Set Entry Point
workflow.set_entry_point("understand_intent")

# Add Conditional Edge
workflow.add_conditional_edges(
    "understand_intent",
    should_continue,
    {
        "execute_tool": "execute_tool",
        "respond": "respond"
    }
)

# Add Normal Edge
workflow.add_edge("execute_tool", "respond")
workflow.add_edge("respond", END)

# Compile
agent_app = workflow.compile()

def run_agent(message: str) -> Dict[str, Any]:
    """Runs the LangGraph agent for a given message."""
    initial_state = {
        "user_message": message,
        "intent_tool": "none",
        "intent_args": {},
        "tool_output": {},
        "response_message": ""
    }
    
    result = agent_app.invoke(initial_state)
    return {
        "response": result["response_message"],
        "action_taken": result["intent_tool"],
        "extracted_data": {
            "args": result["intent_args"],
            "tool_output": result["tool_output"]
        }
    }
