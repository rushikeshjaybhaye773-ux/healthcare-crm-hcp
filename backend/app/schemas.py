from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List

# HCP Schemas
class HCPBase(BaseModel):
    name: str = Field(..., example="Dr. Sharma")
    hospital: str = Field(..., example="Apex Hospital")
    specialization: str = Field(..., example="Cardiologist")

class HCPCreate(HCPBase):
    pass

class HCPResponse(HCPBase):
    id: int

    class Config:
        from_attributes = True

# Interaction Schemas
class InteractionBase(BaseModel):
    meeting_date: date = Field(..., example="2026-07-15")
    summary: Optional[str] = Field(None, example="Discussed CardioPlus with Dr. Sharma.")
    notes: Optional[str] = Field(None, example="Dr. Sharma was positive about CardioPlus. Wants samples next week.")
    products_discussed: Optional[str] = Field(None, example="CardioPlus")
    sentiment: Optional[str] = Field(None, example="Positive")
    action_items: Optional[str] = Field(None, example="Deliver samples next week")
    follow_up: Optional[date] = Field(None, example="2026-07-22")

class InteractionCreate(InteractionBase):
    hcp_id: int

class InteractionResponse(InteractionBase):
    id: int
    hcp_id: int
    created_at: datetime
    hcp: HCPResponse

    class Config:
        from_attributes = True

# AI Chat API Schemas
class ChatRequest(BaseModel):
    message: str = Field(..., example="I met Dr Sharma today. We discussed CardioPlus. He asked for samples.")

class ChatResponse(BaseModel):
    response: str
    action_taken: Optional[str] = None
    extracted_data: Optional[dict] = None
