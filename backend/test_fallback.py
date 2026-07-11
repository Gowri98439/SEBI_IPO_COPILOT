import asyncio
from app.config import settings
settings.LLM_MODEL = "invalid-model-name-123"

from app.ai.llm_client import get_llm
from langchain_core.messages import HumanMessage

async def main():
    llm = get_llm()
    try:
        res = await llm.ainvoke([HumanMessage(content="Hello!")])
        print("Success! Fallback worked. Res:", res.content)
    except Exception as e:
        print("Failed!", str(e))

if __name__ == "__main__":
    asyncio.run(main())
