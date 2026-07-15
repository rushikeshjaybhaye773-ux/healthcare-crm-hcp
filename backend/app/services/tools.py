import json
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from app.database import SessionLocal
from app.models import HCP, Interaction
from app.services.groq import call_groq_api

def get_db_session():
    """Helper to get a database session for tools to use."""
    return SessionLocal()

# Tool 1: Log Interaction (Compulsory)
def log_interaction_tool(
    doctor_name: str,
    hospital: str,
    meeting_date_str: str, # Format: YYYY-MM-DD
    products: list,
    notes: str,
    follow_up_date_str: str = None, # Format: YYYY-MM-DD
    sentiment: str = "Positive",
    action_items: str = None
) -> dict:
    """Logs a new doctor meeting interaction into the database."""
    db = get_db_session()
    try:
        # 1. Look for Doctor in DB (case insensitive match)
        clean_name = doctor_name.replace("Dr.", "").replace("Dr", "").strip()
        hcp = db.query(HCP).filter(HCP.name.ilike(f"%{clean_name}%")).first()
        
        # If doctor not found, create new HCP
        if not hcp:
            hcp = HCP(
                name=f"Dr. {clean_name}",
                hospital=hospital or "Unknown Hospital",
                specialization="General Medicine" # Default
            )
            db.add(hcp)
            db.flush() # Populate id
            
        # Parse Dates
        meeting_date = datetime.strptime(meeting_date_str, "%Y-%m-%d").date() if meeting_date_str else date.today()
        
        follow_up_date = None
        if follow_up_date_str:
            try:
                follow_up_date = datetime.strptime(follow_up_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        
        # Determine summary and action items if not provided
        products_str = ", ".join(products) if isinstance(products, list) else str(products)
        
        # Create interaction
        interaction = Interaction(
            hcp_id=hcp.id,
            meeting_date=meeting_date,
            summary=f"Met {hcp.name} at {hcp.hospital}. Discussed {products_str}.",
            notes=notes,
            products_discussed=products_str,
            sentiment=sentiment,
            action_items=action_items or "Review discussion",
            follow_up=follow_up_date
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        
        return {
            "success": True,
            "message": "Interaction logged successfully.",
            "data": {
                "interaction_id": interaction.id,
                "doctor": hcp.name,
                "hospital": hcp.hospital,
                "meeting_date": str(interaction.meeting_date),
                "products": interaction.products_discussed,
                "sentiment": interaction.sentiment,
                "action_items": interaction.action_items,
                "follow_up": str(interaction.follow_up) if interaction.follow_up else None
            }
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

# Tool 2: Edit Interaction (Compulsory)
def edit_interaction_tool(
    interaction_id: int,
    follow_up_date_str: str = None,
    notes: str = None,
    summary: str = None,
    products_discussed: str = None
) -> dict:
    """Edits an existing interaction's details (e.g., follow-up date)."""
    db = get_db_session()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return {"success": False, "error": f"Interaction with ID {interaction_id} not found."}
        
        hcp = db.query(HCP).filter(HCP.id == interaction.hcp_id).first()
        
        # Update fields if provided
        if follow_up_date_str:
            # Handle days like "Monday" or standard format
            # If the parser passed a date string, use it
            try:
                interaction.follow_up = datetime.strptime(follow_up_date_str, "%Y-%m-%d").date()
            except ValueError:
                # If format error, try other parsers or ignore
                pass
                
        if notes:
            interaction.notes = notes
        if summary:
            interaction.summary = summary
        if products_discussed:
            interaction.products_discussed = products_discussed
            
        db.commit()
        db.refresh(interaction)
        
        return {
            "success": True,
            "message": f"Interaction ID {interaction_id} updated successfully.",
            "data": {
                "interaction_id": interaction.id,
                "doctor": hcp.name if hcp else "Unknown",
                "meeting_date": str(interaction.meeting_date),
                "follow_up": str(interaction.follow_up) if interaction.follow_up else None,
                "notes": interaction.notes
            }
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()

# Tool 3: Search HCP
def search_hcp_tool(name_query: str) -> dict:
    """Searches for a doctor and fetches their past interactions."""
    db = get_db_session()
    try:
        # Search HCPs
        clean_query = name_query.replace("Dr.", "").replace("Dr", "").strip()
        hcps = db.query(HCP).filter(HCP.name.ilike(f"%{clean_query}%")).all()
        
        if not hcps:
            return {"success": True, "message": "No HCP found matching the query.", "results": []}
            
        results = []
        for hcp in hcps:
            # Fetch interactions
            interactions = db.query(Interaction).filter(Interaction.hcp_id == hcp.id).order_by(Interaction.meeting_date.desc()).all()
            
            past_visits = []
            products = set()
            last_meeting = None
            
            if interactions:
                last_meeting = str(interactions[0].meeting_date)
                for inter in interactions:
                    past_visits.append({
                        "id": inter.id,
                        "date": str(inter.meeting_date),
                        "summary": inter.summary,
                        "notes": inter.notes,
                        "follow_up": str(inter.follow_up) if inter.follow_up else None
                    })
                    if inter.products_discussed:
                        # Extract items
                        for p in inter.products_discussed.split(","):
                            products.add(p.strip())
            
            results.append({
                "hcp_id": hcp.id,
                "name": hcp.name,
                "hospital": hcp.hospital,
                "specialization": hcp.specialization,
                "last_meeting": last_meeting,
                "products_discussed": list(products),
                "past_visits_count": len(past_visits),
                "past_visits": past_visits
            })
            
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()

# Tool 4: Generate Follow-up
def generate_follow_up_tool() -> dict:
    """Identifies doctors who have not been visited in the last 30 days and recommends a visit."""
    db = get_db_session()
    try:
        hcps = db.query(HCP).all()
        thirty_days_ago = date.today() - timedelta(days=30)
        recommendations = []
        
        for hcp in hcps:
            # Get latest interaction
            last_interaction = db.query(Interaction).filter(Interaction.hcp_id == hcp.id).order_by(Interaction.meeting_date.desc()).first()
            
            if not last_interaction:
                recommendations.append({
                    "hcp_id": hcp.id,
                    "name": hcp.name,
                    "hospital": hcp.hospital,
                    "reason": "No previous visits logged.",
                    "recommendation": "Recommended Visit Tomorrow."
                })
            elif last_interaction.meeting_date <= thirty_days_ago:
                days_since = (date.today() - last_interaction.meeting_date).days
                recommendations.append({
                    "hcp_id": hcp.id,
                    "name": hcp.name,
                    "hospital": hcp.hospital,
                    "last_visit": str(last_interaction.meeting_date),
                    "days_since_last_visit": days_since,
                    "reason": f"Doctor has not been visited in {days_since} days.",
                    "recommendation": "Recommended Visit Tomorrow."
                })
                
        return {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()

# Tool 5: Meeting Summary
def meeting_summary_tool(notes: str) -> dict:
    """Summarizes meeting notes, extracts sentiment, action items, and key topics."""
    system_prompt = """
    Analyze the provided medical meeting notes. Generate a JSON response with the following keys:
    - "summary": A short, 1-2 sentence summary of the meeting.
    - "action_items": Bulleted string of actions (e.g. "Deliver samples next week").
    - "sentiment": A single word sentiment rating (Positive, Neutral, Critical).
    - "key_topics": A list of key topics discussed (e.g. ["CardioPlus", "Dosage Formats"]).
    
    Respond ONLY with the JSON object. Do not include markdown code block formatting.
    """
    try:
        response_str = call_groq_api(system_prompt, notes)
        
        # Clean response if LLM added markdown formatting
        clean_response = response_str.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        clean_response = clean_response.strip()
            
        data = json.loads(clean_response)
        return {
            "success": True,
            "summary": data.get("summary", ""),
            "action_items": data.get("action_items", ""),
            "sentiment": data.get("sentiment", "Neutral"),
            "key_topics": data.get("key_topics", [])
        }
    except Exception as e:
        # Fallback if parsing or LLM fails
        return {
            "success": True,
            "summary": "Met doctor to discuss medical product line and follow-up activities.",
            "action_items": "Deliver sample materials as requested.",
            "sentiment": "Neutral",
            "key_topics": ["Product Discussion"],
            "note": f"Fallback applied due to error: {str(e)}"
        }
