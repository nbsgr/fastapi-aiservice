# ==========================================
# FASTAPI AI SERVICE (INCEPTIONLABS / OPENAI COMPATIBLE)
# ==========================================
import os
import time
import logging
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from intent_processor import intent_processing
from generator import get_client, DEFAULT_MODEL

# ==========================================
# LOGGING
# ==========================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# ==========================================
# FASTAPI APP
# ==========================================
app = FastAPI(title="FastAPI AI Service", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False
)

# ==========================================
# INTENT CLASSIFICATION (USING INCEPTIONLABS / OPENAI)
# ==========================================
def classify_intent(query: str, client, model: str) -> str:
    start_time = time.time()
    logger.info("================ INTENT CLASSIFICATION STARTED ================")
    logger.info(f"Classify query: {query}")

    # Fast small-talk shortcut
    small_talk_inputs = {"hi", "hello", "hey", "hii", "yo", "sup", "good morning", "good afternoon", "good evening", "good night"}
    normalized_query = query.lower().strip()

    if normalized_query in small_talk_inputs:
        logger.info("[INTENT] Small talk shortcut matched -> SMALL_TALK")
        return "SMALL_TALK"

    system_prompt = """Return ONLY either:
WEB_SEARCH or
DIRECT

Return WEB_SEARCH for:
- latest, current, recent, news, stock prices, weather, sports results, changing facts, live websites

Return DIRECT for:
- programming, coding, algorithms, explanations, tutorials, concepts, history, general conversation
"""

    try:
        response = client.chat.completions.create(
            model=model or DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.0,
            max_tokens=5
        )
        result = response.choices[0].message.content.strip().upper()
        if "WEB_SEARCH" in result:
            logger.info("[INTENT] Classified as: WEB_SEARCH")
            return "WEB_SEARCH"
        logger.info("[INTENT] Classified as: DIRECT")
        return "DIRECT"
    except Exception as e:
        logger.warning(f"[INTENT ERROR] Exception during classification: {e}, falling back to DIRECT")
        return "DIRECT"

# ==========================================
# ROOT & HEALTH CHECK ENDPOINTS
# ==========================================
@app.get("/")
def root():
    return {
        "status": 200,
        "message": "FastAPI AI Service is online and running successfully!",
        "provider": os.getenv("AI_PROVIDER", "inceptionlabs"),
        "default_model": os.getenv("DEFAULT_MODEL", "mercury-2")
    }

@app.get("/api/health-check")
def health_check():
    """Health check endpoint that verifies AI provider connectivity and returns available models"""
    try:
        ai_client = get_client()
        models = ai_client.models.list()
        model_names = [m.id for m in models.data]
        return {
            "status": 200,
            "message": "AI Service Health Check Passed",
            "provider": os.getenv("AI_PROVIDER", "inceptionlabs"),
            "default_model": os.getenv("DEFAULT_MODEL", "mercury-2"),
            "available_models": model_names
        }
    except Exception as e:
        return {
            "status": 500,
            "message": "AI Service Health Check Failed",
            "error": str(e)
        }

@app.get("/api/models")
def list_models():
    """List available models from the configured AI provider"""
    try:
        ai_client = get_client()
        models = ai_client.models.list()
        return {
            "status": 200,
            "data": [m.id for m in models.data]
        }
    except Exception as e:
        return {"status": 500, "error": str(e)}

# ==========================================
# MAIN STREAM API: /api/process-stream
# ==========================================
@app.post("/api/process-stream")
async def process_stream(request: Request):
    data = await request.json()
    query = data.get("question", "").strip()
    messages = data.get("messages", [])

    # User-customizable parameters
    model = data.get("model") or os.getenv("DEFAULT_MODEL", "mercury-2")
    base_url = data.get("base_url") or None
    api_key = data.get("api_key") or None

    logger.info("============ API REQUEST RECEIVED ============")
    logger.info(f"[API HIT] QUERY: {query}")
    logger.info(f"[API HIT] MODEL: {model}")
    logger.info(f"[API HIT] MESSAGES COUNT: {len(messages) if isinstance(messages, list) else 0}")

    if not query:
        logger.warning("[API REQUEST IS EMPTY] Empty question received")
        return JSONResponse({"error": "Empty question received"}, status_code=400)

    ai_client = get_client(base_url, api_key)
    intent = classify_intent(query, ai_client, model)

    def stream_generator():
        yield from intent_processing(
            query=query,
            intent=intent,
            messages=messages,
            model=model,
            base_url=base_url,
            api_key=api_key
        )

    return StreamingResponse(
        stream_generator(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

# ==========================================
# SERVER RUNNER
# ==========================================
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    logger.info(f"Starting FastAPI AI Service on {host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
