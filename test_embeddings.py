from app.ai.embeddings import get_embeddings
import asyncio

async def test():
    emb = get_embeddings()
    res = await emb.aembed_query("test query")
    print("Embedding returned, length:", len(res))

asyncio.run(test())
