import asyncio
from app.ai.llm_client import get_llm
from app.ai.embeddings import get_embeddings
from langchain_core.messages import HumanMessage

async def test_llm():
    try:
        llm = get_llm()
        res = await llm.ainvoke([HumanMessage(content="Hello! Are you working?")])
        print("LLM Success! Response:", res.content)
    except Exception as e:
        print("LLM Failed:", e)

async def test_embeddings():
    try:
        emb = get_embeddings()
        res = await emb.aembed_query("Hello")
        print("Embeddings Success! Length:", len(res))
    except Exception as e:
        print("Embeddings Failed:", e)

async def main():
    await test_llm()
    await test_embeddings()

if __name__ == "__main__":
    asyncio.run(main())
