import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.database import engine, Base, SessionLocal
from app.routers.interaction import router as interaction_router
import app.models as models

load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Healthcare CRM - HCP Module API",
    description="Backend API with LangGraph agent support to log and manage interactions with HCPs",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, lock this down
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seed database on startup
@app.on_event("startup")
def seed_data():
    db = SessionLocal()
    try:
        # Check if HCPs already exist
        if db.query(models.HCP).count() == 0:
            print("Seeding database with sample HCPs...")
            sample_hcps = [
                models.HCP(name="Dr. Sharma", hospital="Apex Hospital", specialization="Cardiologist"),
                models.HCP(name="Dr. Patil", hospital="City Hospital", specialization="Pediatrician"),
                models.HCP(name="Dr. Verma", hospital="Grace Clinic", specialization="Orthopedic Surgeon"),
                models.HCP(name="Dr. Iyer", hospital="Medipoint Healthcare", specialization="Pharmacist"),
                models.HCP(name="Dr. Kulkarni", hospital="Care Hospital", specialization="Physician")
            ]
            db.add_all(sample_hcps)
            db.commit()
            
            # Add some past interactions for testing
            hcps = db.query(models.HCP).all()
            from datetime import date, timedelta
            
            # Dr Sharma: visited 35 days ago (should show up in recommendations!)
            db.add(models.Interaction(
                hcp_id=hcps[0].id,
                meeting_date=date.today() - timedelta(days=35),
                summary="Discussed CardioPlus side effects and dosage details.",
                notes="Dr. Sharma has concerns about the 10mg dosage side effects. Requested more clinical study reports.",
                products_discussed="CardioPlus",
                sentiment="Neutral",
                action_items="Send clinical trial brochure",
                follow_up=date.today() - timedelta(days=28)
            ))
            
            # Dr Patil: visited 10 days ago (recent)
            db.add(models.Interaction(
                hcp_id=hcps[1].id,
                meeting_date=date.today() - timedelta(days=10),
                summary="Introductory meeting regarding KidMed vitamins.",
                notes="Dr. Patil was excited about KidMed gummy format. Positive meeting, agreed to display brochures in waiting room.",
                products_discussed="KidMed Gummy",
                sentiment="Positive",
                action_items="Provide 5 brochure stands",
                follow_up=date.today() + timedelta(days=14)
            ))
            db.commit()
            print("Seeding complete.")
    except Exception as e:
        print(f"Error seeding database: {str(e)}")
    finally:
        db.close()

# Include routers
app.include_router(interaction_router)

@app.get("/")
def read_root():
    return {
        "name": "Healthcare CRM API",
        "status": "online",
        "agent": "LangGraph Active",
        "documentation": "/docs"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
