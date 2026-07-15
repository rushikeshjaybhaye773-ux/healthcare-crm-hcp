from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class HCP(Base):
    __tablename__ = "hcp"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    hospital = Column(String(255), nullable=False)
    specialization = Column(String(255), nullable=False)

    interactions = relationship("Interaction", back_populates="hcp", cascade="all, delete-orphan")

class Interaction(Base):
    __tablename__ = "interaction"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcp.id", ondelete="CASCADE"), nullable=False)
    meeting_date = Column(Date, nullable=False)
    summary = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    products_discussed = Column(String(500), nullable=True)
    sentiment = Column(String(50), nullable=True)
    action_items = Column(Text, nullable=True)
    follow_up = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")
