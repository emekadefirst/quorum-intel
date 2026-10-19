import os

from dotenv import load_dotenv

load_dotenv()

# "anthropic" | "google-gemini" | "deepseek" | "openai" | "qwen"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "")  # override for OpenAI-compatible
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))
