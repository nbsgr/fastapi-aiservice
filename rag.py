import time, logging
import requests


# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# =====================================================
# CONFIG
# =====================================================

OLLAMA_URL = "http://localhost:11434/api/embed"
MODEL="nomic-embed-text-v2-moe:latest"

TOP_K=4
CHUNK_SIZE=1024
CHUNK_OVERLAP=200
SIMILARITY_THRESHOLD=0.22
MAX_CHUNKS=120


OLLAMA_OPTIONS={
    "num_ctx":6
}

# =====================================================
# HTTP SESSION
# =====================================================
session = requests.Session()
# =====================================================
# CHUNK TEXT
# =====================================================

def chunk_text(text:str):
    chunks = []
    start = 0
    #chek chunks
    while start < len(text):
        end=start+CHUNK_SIZE
        chunks.append(text[start:end])
        start+=CHUNK_SIZE-CHUNK_OVERLAP
    chunks=chunks[:MAX_CHUNKS]
    return chunks

# =====================================================
# GENERATE EMBEDDING
# =====================================================

def generate_embedding(text:str):
    if not text:
        logger.warning("Failed to generate embedding")
        return []
    logger.info(f"[EMBEDDING] TEXT LENGTH={len(text)}")
    try:
        response = session.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "input": text
            },timeout=60)
        if response.status_code != 200:
            logger.error(f"[EMBEDDING] STATUS={response.status_code}")
            return []
        data = response.json()
        embeddings = data.get("embeddings",[])
        embeddings=embeddings[0]
        if not  embeddings:
            logger.error(f"[EMBEDDING] EMPTY RESPONSE")
            return []
        logger.info(f"[EMBEDDING] VECTOR SIZE={len(embeddings)}")
        return embeddings
    except Exception as e:
        logger.error(f"[EMBEDDING]: {e}")
        return []



import math

# =====================================================
# COSINE SIMILARITY (LIGHTWEIGHT PURE PYTHON FOR SERVERLESS)
# =====================================================
def cosine_similarity_check(vec1: list, vec2: list):
    if not vec1 or not vec2:
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a, b in zip(vec1, vec2)))
    norm_b = math.sqrt(sum(b * b for a, b in zip(vec1, vec2)))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot_product / (norm_a * norm_b))

# =====================================================
# RETRIEVE CONTEXT
# =====================================================

def retrieve_context(query:str,scrape_result:dict):
    start_time=time.time()
    logger.info("===========RAG PIPELINE STARTED==========")

    #Empty query check
    if not query or not query.strip():
        logger.error("[RAG] EMPTY QUERY")
        return {
            "success": False,
            "context": "",
            "sources": [],
            "count": 0,
            "timeMs": 0
        }

    #check whether the scrape_result is success or not
    if not scrape_result.get("success"):
        logger.error(f"[RAG] FAILED FOR QUERY: {query},{scrape_result}")
        return {
            "success":False,
            "context":"",
            "sources":[],
            "count":0,
            "timeMs":0
        }

    #get the documents
    documents=scrape_result.get("documents",[])

    #check whether documents are empty
    if not documents:
        logger.error(f"[RAG] FAILED FOR DOCUMENTS: {query},{documents}")
        return {
            "success":False,
            "context":"",
            "sources":[],
            "count":0,
            "timeMs":0
        }

    #Get the query embeddings
    query_embedding=generate_embedding(query)
    if not query_embedding:
        logger.warning("[RAG] Embeddings unavailable (e.g. running in serverless), using direct text snippets fallback")
        fallback_texts = []
        sources = []
        for doc in documents[:3]:
            txt = doc.get("text", "")
            u = doc.get("url", "")
            if txt:
                fallback_texts.append(f"Source ({u}):\n{txt[:1200]}")
                sources.append(u)
        return {
            "success": True,
            "context": "\n\n".join(fallback_texts),
            "sources": sources,
            "count": len(sources),
            "timeMs": int((time.time() - start_time) * 1000)
        }

    #documents to chunks
    all_chunks=[]
    for document in documents:
        text =document.get("text","")
        url=document.get("url","")
        if not text:
            logger.error(f"[RAG] EMPTY TEXT : {text},{url}")
            continue
        logger.info(f"[RAG] URL = {url}")

        #call the chunk_text function
        chunks=chunk_text(text)
        if not chunks:
            logger.error(f"[RAG] NO CHUNKS GENERATED: {url}")
            continue
        logger.info(f"[RAG] GENERATED {len(chunks)} CHUNKS FOR {url}")

        #building chunks from all the urls
        for chunk in chunks:
            all_chunks.append({
                "url":url,
                "text":chunk
            })
    #logging how many chunks we got in main chunk
    logger.info(f"[RAG] TOTAL CHUNKS FOR {len(all_chunks)}")

    #check whether chunks are actually there or not
    if not all_chunks:
        logger.error(f"[RAG] EMPTY CHUNKS FOR {url}")
        return {
            "success":False,
            "context":"",
            "sources":[],
            "count":0,
            "timeMs":int((time.time()-start_time)*1000)
        }

    #build the combined chunks
    stored_chunks=[]
    for chunk in all_chunks:
        #get the chunks
        chunk_text_data=chunk.get("text","")

        #get the url to which chunk belong
        chunk_url=chunk.get("url","")
        logger.info(f"[RAG] GENERATING EMBEDDING FOR {chunk_url}")

        #call the generate_embedding function
        chunk_embedding=generate_embedding(chunk_text_data)

        #check whether embedding are returned or not
        if not chunk_embedding:
            logger.warning(f"[RAG] EMPTY EMBEDDING FOR {chunk_url}")
            continue

        #check for the similarity also
        similarity=cosine_similarity_check(query_embedding,chunk_embedding)
        logger.info(f"[RAG] SIMILARITY={similarity:.4f} URL={chunk_url}")

        #compare the similarity with our threshold value
        if similarity<SIMILARITY_THRESHOLD:
            logger.info(f"[RAG] BELOW THRESHOLD ={similarity:.4f} URL={chunk_url}")
            continue

        #append the url and text and score to the stored chunks
        stored_chunks.append({
            "url":chunk_url,
            "text":chunk_text_data,
            "score":similarity,
        })
    logger.info(f"[RAG] RELEVANT CHUNKS: {len(stored_chunks)}")
    if not stored_chunks:
        return {
            "success":False,
            "context":"",
            "sources":[],
            "count":0,
            "timeMs":int((time.time()-start_time)*1000)
        }
    stored_chunks.sort(key=lambda chunk:chunk["score"], reverse=True)
    top_chunks=stored_chunks[:TOP_K]
    logger.info(f"[RAG] TOP_CHUNKS: {len(top_chunks)}")
    context_parts=[]
    sources=[]
    # context building
    for chunk in top_chunks:
        context_parts.append(
            f"Source: {chunk['url']}\n"
            f"{chunk['text']}"
        )
        sources.append(chunk["url"])
    #full context
    context = "\n\n".join(context_parts)
    logger.info(f"[RAG] CONTEXT LENGTH={len(context)}")

    #remove duplicate sources
    sources = list(set(sources))

    #log complete sources
    logger.info(f"[RAG] SOURCES {len(sources)}")
    logger.info(
        f"[RAG] COMPLETED | "
        f"CHUNKS={len(top_chunks)} | "
        f"SOURCES={len(sources)} | "
        f"TIME={int((time.time() - start_time) * 1000)}ms"
    )

    #at last return the output
    return {
        "success": True,
        "context": context,
        "sources": sources,
        "count": len(top_chunks),
        "timeMs": int((time.time() - start_time) * 1000)
    }











