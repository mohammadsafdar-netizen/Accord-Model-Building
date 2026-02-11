import os
from typing import List, Dict, Any, Tuple
# from langchain_groq import ChatGroq (Deprecated)
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.schemas import CommonInsuranceData
from src.tools.form_population import get_tooltip_for_field

# Singleton for LLM
_llm = None

def _get_llm():
    global _llm
    if _llm is None:
        # Switching to llama3.2 (3B) for faster performance
        _llm = ChatOllama(
            model="llama3.2",
            temperature=0.1, # Low temp for precision
            base_url="http://localhost:11434" # Default Ollama URL
        )
    return _llm

def generate_next_question(unfilled_fields: List[str], current_phase: str) -> Tuple[str, str, str]:
    """
    Generates next question using LLM, leveraging PDF field tooltips and Pydantic descriptions.
    """
    if not unfilled_fields:
        return "All required information has been collected. Is there anything else you'd like to check before we proceed?", "none", "statement"
    
    field = unfilled_fields[0]
    
    # First, try to get tooltip from PDF (most accurate for ACORD forms)
    field_description = ""
    try:
        pdf_tooltip = get_tooltip_for_field(field)
        if pdf_tooltip:
            field_description = pdf_tooltip
    except Exception:
        pass
    
    # Fallback to Pydantic description if no PDF tooltip
    if not field_description:
        try:
            field_info = CommonInsuranceData.model_fields.get(field)
            if field_info and field_info.description:
                field_description = field_info.description
        except Exception:
            pass
    
    try:
        llm = _get_llm()
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful insurance assistant. Your goal is to politely and clearly ask the user for a specific piece of information. Be concise. Use the field instructions provided to guide your question."),
            ("human", "Please ask the user for their '{field}'. Field Instructions: {description}. The current phase is '{phase}'. Keep it professional but conversational. Do not ask multiple questions. Do not repeat the raw field name, instead paraphrase it naturally.")
        ])
        chain = prompt | llm | StrOutputParser()
        question = chain.invoke({"field": field, "description": field_description or "N/A", "phase": current_phase})
        
        # Fallback if LLM fails or returns empty
        if not question:
            question = f"Please provide your {field}."
            
    except Exception as e:
        print(f"LLM Error in generate_next_question: {e}")
        question = f"Please provide your {field}."

    return question, field, "text"

def generate_reflection_response(user_input: str, field_name: str, error_msg: str) -> str:
    """
    AGENTIC PATTERN: REFLECTION
    Generates a helpful, corrective response when validation fails, instead of a dry error.
    """
    try:
        llm = _get_llm()
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an empathetic, intelligent insurance agent. The user provided invalid input for a form field. Your goal is to acknowledge their input, explain gently why it doesn't fit the requirement, and suggest how to fix it or offer a valid alternative format. Be helpful, not robotic."),
            ("human", "Field: {field}\nUser Input: '{input}'\nSystem Error: {error}\n\nPlease generate a natural language response to correct the user/guide them.")
        ])
        chain = prompt | llm | StrOutputParser()
        response = chain.invoke({"field": field_name, "input": user_input, "error": error_msg})
        return response
    except Exception as e:
        print(f"LLM Error in reflection: {e}")
        return f"I wasn't able to understand that input. {error_msg} Could you try again?"

def generate_planning_message(prev_phase: str, next_phase: str) -> str:
    """
    AGENTIC PATTERN: PLANNING
    Generates a transitional message that explains the 'Plan' to the user when switching contexts.
    """
    try:
        llm = _get_llm()
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a professional insurance strategist. You are moving the user from one section of the application to another. Briefly explain what we just finished and what we are moving to next, so the user has a sense of progress."),
            ("human", "Finished Section: {prev}\nNext Section: {next}\n\nGenerate a 1-sentence transition message.")
        ])
        chain = prompt | llm | StrOutputParser()
        response = chain.invoke({"prev": prev_phase, "next": next_phase})
        return response
    except Exception as e:
        return f"Moving from {prev_phase} to {next_phase}..."

def classify_user_intent(user_message: str) -> Tuple[str, float]:
    """
    Classifies user intent using LLM.
    """
    try:
        llm = _get_llm()
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an intent classifier for an insurance form bot. Classify the user's message into one of these categories: 'cancel', 'submit', 'ask_question', 'provide_info'. Return ONLY the category name, nothing else."),
            ("human", "User Message: {message}")
        ])
        chain = prompt | llm | StrOutputParser()
        intent = chain.invoke({"message": user_message}).strip().lower()
        
        valid_intents = ['cancel', 'submit', 'ask_question', 'provide_info']
        if intent not in valid_intents:
            # simple heuristic fallback
            if "?" in user_message: return "ask_question", 0.8
            if "stop" in user_message.lower(): return "cancel", 0.9
            return "provide_info", 0.8
            
        return intent, 0.9
        
    except Exception as e:
        print(f"LLM Error in classify_user_intent: {e}")
        return "provide_info", 0.5 # Default

def track_conversation_context(new_message: str, history: List[Dict]) -> List[Dict]:
    """
    Simple appender for context.
    """
    entry = {"role": "user", "content": new_message}
    return history + [entry]

def calculate_form_progress(filled_params: int, total_params: int) -> Tuple[float, int]:
    if total_params == 0:
        return 100.0, 0
    
    pct = (filled_params / total_params) * 100
    return round(pct, 1), total_params - filled_params
