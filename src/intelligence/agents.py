from langchain.agents import create_agent

from src.intelligence.prompts import (
    SCHEME_GENERATION_PROMPT,
    APPLICATION_PROCESSING_PROMPT,
)
from src.intelligence.tools import (
    screening_tools,
    classifying_tools,
)
from src.intelligence.llm import model



classifying_agent = create_agent(
    model=model,
    tools=classifying_tools,
    system_prompt=SCHEME_GENERATION_PROMPT,
)


screening_agent = create_agent(
    model=model,
    tools=screening_tools,
    system_prompt=APPLICATION_PROCESSING_PROMPT,
)
