import os
from langchain_groq import ChatGroq

# Initialize LLM
def initialize_llm():
    return ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.1-8b-instant",
        temperature=0.0,
        max_tokens=4096,
    )
