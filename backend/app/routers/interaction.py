from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import List
from app.database import get_db
import app.models as models
import app.schemas as schemas
from app.services.langgraph_agent import run_agent
from app.services.tools import generate_follow_up_tool

router = APIRouter(prefix="/api", tags=["interactions"])

@router.get("/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Fetch counts and recent items for the main dashboard."""
    today = date.today()
    total_interactions = db.query(models.Interaction).count()
    today_meetings = db.query(models.Interaction).filter(models.Interaction.meeting_date == today).count()
    upcoming_followups = db.query(models.Interaction).filter(models.Interaction.follow_up >= today).count()
    
    recent_interactions = db.query(models.Interaction).order_by(models.Interaction.created_at.desc()).limit(5).all()
    
    # Recommendations
    recs = generate_follow_up_tool()
    recommended_count = len(recs.get("recommendations", []))
    
    return {
        "stats": {
            "total_interactions": total_interactions,
            "today_meetings": today_meetings,
            "upcoming_followups": upcoming_followups,
            "recommended_visits": recommended_count
        },
        "recent_interactions": [
            {
                "id": item.id,
                "doctor_name": item.hcp.name if item.hcp else "Unknown",
                "hospital": item.hcp.hospital if item.hcp else "Unknown",
                "specialization": item.hcp.specialization if item.hcp else "Unknown",
                "meeting_date": str(item.meeting_date),
                "products": item.products_discussed,
                "summary": item.summary,
                "sentiment": item.sentiment,
                "follow_up": str(item.follow_up) if item.follow_up else None
            }
            for item in recent_interactions
        ]
    }

@router.get("/hcps", response_model=List[schemas.HCPResponse])
def get_hcps(db: Session = Depends(get_db)):
    """List all HCPs."""
    return db.query(models.HCP).all()

@router.post("/hcps", response_model=schemas.HCPResponse)
def create_hcp(hcp: schemas.HCPCreate, db: Session = Depends(get_db)):
    """Create a new Healthcare Professional."""
    db_hcp = db.query(models.HCP).filter(models.HCP.name.ilike(hcp.name.strip())).first()
    if db_hcp:
         return db_hcp
    new_hcp = models.HCP(
        name=hcp.name,
        hospital=hcp.hospital,
        specialization=hcp.specialization
    )
    db.add(new_hcp)
    db.commit()
    db.refresh(new_hcp)
    return new_hcp

@router.get("/interactions", response_model=List[schemas.InteractionResponse])
def get_interactions(db: Session = Depends(get_db)):
    """List all interactions."""
    return db.query(models.Interaction).order_by(models.Interaction.meeting_date.desc()).all()

@router.post("/interactions", response_model=schemas.InteractionResponse)
def log_structured_interaction(payload: schemas.InteractionCreate, db: Session = Depends(get_db)):
    """Log an interaction from the structured form."""
    hcp = db.query(models.HCP).filter(models.HCP.id == payload.hcp_id).first()
    if not hcp:
        raise HTTPException(status_code=404, detail="HCP not found")
        
    db_interaction = models.Interaction(
        hcp_id=payload.hcp_id,
        meeting_date=payload.meeting_date,
        summary=payload.summary or f"Met {hcp.name}. Discussed {payload.products_discussed or 'products'}.",
        notes=payload.notes,
        products_discussed=payload.products_discussed,
        sentiment=payload.sentiment or "Neutral",
        action_items=payload.action_items,
        follow_up=payload.follow_up
    )
    db.add(db_interaction)
    db.commit()
    db.refresh(db_interaction)
    return db_interaction

@router.post("/chat", response_model=schemas.ChatResponse)
def chat_with_agent(payload: schemas.ChatRequest):
    """Chat endpoint to communicate with LangGraph AI Agent."""
    try:
        agent_result = run_agent(payload.message)
        return schemas.ChatResponse(
            response=agent_result["response"],
            action_taken=agent_result["action_taken"],
            extracted_data=agent_result["extracted_data"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent workflow error: {str(e)}"
        )

@router.put("/interactions/{interaction_id}", response_model=schemas.InteractionResponse)
def edit_interaction(interaction_id: int, payload: schemas.InteractionBase, db: Session = Depends(get_db)):
    """Update details of an interaction."""
    db_interaction = db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
    if not db_interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
        
    db_interaction.meeting_date = payload.meeting_date
    db_interaction.summary = payload.summary
    db_interaction.notes = payload.notes
    db_interaction.products_discussed = payload.products_discussed
    db_interaction.sentiment = payload.sentiment
    db_interaction.action_items = payload.action_items
    db_interaction.follow_up = payload.follow_up
    
    db.commit()
    db.refresh(db_interaction)
    return db_interaction
