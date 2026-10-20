from langchain.agents import create_agent

from src.intelligence.llm import model
from src.intelligence.prompts import TRADING_AGENT_PROMPT
from src.intelligence.tools import trading_tools

trading_agent = create_agent(
    model=model,
    tools=trading_tools,
    system_prompt=TRADING_AGENT_PROMPT,
)
