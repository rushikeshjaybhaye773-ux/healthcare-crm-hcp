import os
import json
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

class MockGroqLLM:
    """Mock Groq LLM client that parses strings using rules/regex when API key is missing."""
    
    def generate_chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        # Check if the system prompt is expecting a JSON block for structured extraction
        if "JSON" in system_prompt or "json" in system_prompt:
            return self._mock_structured_extraction(user_prompt)
        
        # Check if it's summary extraction
        if "summary" in system_prompt.lower() or "summarize" in system_prompt.lower():
            return self._mock_summary(user_prompt)
            
        return f"AI Response (Mock): I processed your request: '{user_prompt}'"

    def _mock_structured_extraction(self, text: str) -> str:
        # Mock structured data extraction from text to align with LangGraph intent node
        text_lower = text.lower()
        
        # Extract doctor name
        doc_match = re.search(r"Dr\.\s*([a-zA-Z]+)", text, re.IGNORECASE)
        doctor = f"Dr. {doc_match.group(1).capitalize()}" if doc_match else "Dr. Sharma"
        
        # Extract products
        prod_match = re.search(r"(CardioPlus|Lipitor|Metformin|Amoxicillin|Aspirin|Insulin|KidMed)", text, re.IGNORECASE)
        product = prod_match.group(1) if prod_match else "CardioPlus"
        
        # Follow up date matching
        follow_up_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        if "friday" in text_lower:
            today = datetime.now()
            days_ahead = 4 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            follow_up_date = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        elif "monday" in text_lower:
            today = datetime.now()
            days_ahead = 0 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            follow_up_date = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        elif "tuesday" in text_lower:
            today = datetime.now()
            days_ahead = 1 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            follow_up_date = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        elif "next week" in text_lower:
            follow_up_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        # Determine intent tool and arguments
        if "search" in text_lower:
            tool = "search_hcp"
            # Get doctor name from search query
            search_doc = text.replace("Search", "").replace("search", "").replace("Doctor", "").replace("doctor", "").replace("Dr.", "").replace("Dr", "").strip()
            args = {
                "name_query": search_doc or "Sharma"
            }
        elif "change" in text_lower or "edit" in text_lower or "update" in text_lower:
            tool = "edit_interaction"
            numbers = [int(s) for s in re.findall(r'\d+', text)]
            args = {
                "interaction_id": numbers[0] if numbers else 25,
                "follow_up_date_str": follow_up_date
            }
        elif "who" in text_lower or "recommend" in text_lower or "should i visit" in text_lower or "recommended" in text_lower:
            tool = "generate_follow_up"
            args = {}
        elif "summarize" in text_lower or "summary" in text_lower:
            tool = "meeting_summary"
            args = {
                "notes": text
            }
        else:
            tool = "log_interaction"
            args = {
                "doctor_name": doctor,
                "hospital": "Apex Hospital" if "apex" in text_lower else "City Hospital",
                "meeting_date_str": datetime.now().strftime("%Y-%m-%d"),
                "products": [product],
                "notes": text,
                "follow_up_date_str": follow_up_date
            }
            
        data = {
            "tool": tool,
            "args": args
        }
        return json.dumps(data)

    def _mock_summary(self, text: str) -> str:
        # Generate summary format
        data = {
            "summary": "Completed routine visit with doctor to discuss core product line.",
            "action_items": "Deliver sample materials as requested.",
            "sentiment": "Positive",
            "key_topics": ["Product Discussion", "Samples Request"]
        }
        return json.dumps(data)

def call_groq_api(system_prompt: str, user_prompt: str) -> str:
    """Calls Groq API using gemma2-9b-it if available, else falls back to Mock client."""
    if not GROQ_API_KEY:
        mock_llm = MockGroqLLM()
        return mock_llm.generate_chat_completion(system_prompt, user_prompt)
        
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="gemma2-9b-it",
            temperature=0.1,
            max_tokens=1000
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Error calling Groq API: {str(e)}. Falling back to mock client.")
        mock_llm = MockGroqLLM()
        return mock_llm.generate_chat_completion(system_prompt, user_prompt)
