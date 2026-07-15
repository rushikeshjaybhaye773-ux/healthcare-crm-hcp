# AI-First CRM HCP Module

## Project Overview

This project is an AI-powered Healthcare CRM system designed for Medical Representatives to log and manage Healthcare Professional (HCP) interactions.

Users can log interactions using:
- Structured Form
- AI Chat Interface

The application uses LangGraph as an AI agent framework with Groq LLM for intelligent interaction management.

---

## Features

- Dashboard
- Log Interaction (Form)
- Log Interaction (Chat)
- AI Meeting Summary
- Search HCP
- Edit Interaction
- Follow-up Recommendations
- LangGraph AI Agent
- FastAPI Backend
- React + Redux Frontend

---

## Tech Stack

### Frontend
- React
- Redux Toolkit
- Vite

### Backend
- Python
- FastAPI

### AI
- LangGraph
- Groq API
- Gemma2-9B-IT

### Database
- SQLite (can be replaced with MySQL/PostgreSQL)

---

## Project Structure

```
HEALTHCARE_CRM
│
├── backend
│   ├── app
│   ├── services
│   ├── routers
│   ├── main.py
│   └── requirements.txt
│
├── frontend
│   ├── src
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

---

## AI Agent Workflow

User

↓

LangGraph Agent

↓

Intent Detection

↓

Tool Selection

↓

Groq LLM

↓

Execute Tool

↓

Database

↓

Response

---

## LangGraph Tools

- Log Interaction
- Edit Interaction
- Search HCP
- Generate Follow-up
- Meeting Summary

---

## Installation

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Future Improvements

- Authentication
- Multi-user Support
- Email Notifications
- Analytics Dashboard
- Voice Interaction

---

## Author

Rushikesh Nandu Jaybhaye