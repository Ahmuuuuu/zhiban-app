from pathlib import Path
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent.parent.parent / ".env")

api_key = os.getenv("api_key")

llm = ChatOpenAI(
    model=os.getenv("AI_MODEL", "deepseek-chat"),
    api_key=api_key,
    base_url=os.getenv("AI_BASE_URL", "https://api.deepseek.com"),
    temperature=0.3,
    streaming=True,
    model_kwargs={"tool_choice": "auto"},
)
