# ==========================================
# GENERATOR (OPENAI-COMPATIBLE STREAMING)
# ==========================================
import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Default config
DEFAULT_BASE_URL = os.getenv("AI_BASE_URL", "https://api.inceptionlabs.ai/v1")
DEFAULT_API_KEY = os.getenv("AI_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "mercury-2")

# Shared OpenAI Client
client = OpenAI(
    base_url=DEFAULT_BASE_URL,
    api_key=DEFAULT_API_KEY
)

# ==========================================
# GET CUSTOM CLIENT (SUPPORTS PER-REQUEST OVERRIDE)
# ==========================================
def get_client(base_url: str = None, api_key: str = None):
    if base_url or api_key:
        return OpenAI(
            base_url=base_url or DEFAULT_BASE_URL,
            api_key=api_key or DEFAULT_API_KEY
        )
    return client

# ==========================================
# STREAM OPENAI CHAT COMPLETION AS NDJSON
# ==========================================
def stream_chat(messages: list, model: str = None, base_url: str = None, api_key: str = None):
    selected_model = model or DEFAULT_MODEL
    ai_client = get_client(base_url, api_key)

    logger.info(f"[GENERATOR] Streaming with model: {selected_model}")
    logger.info(f"[GENERATOR] Messages count: {len(messages)}")

    try:
        response = ai_client.chat.completions.create(
            model=selected_model,
            messages=messages,
            stream=True
        )

        for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            content = getattr(delta, "content", "") or ""
            # Support reasoning/thinking tokens if provided by provider
            thinking = getattr(delta, "reasoning_content", "") or getattr(delta, "thinking", "") or ""

            # Format matching the NDJSON expected by frontend ChatSpace.jsx
            node = {
                "model": selected_model,
                "message": {
                    "role": "assistant",
                    "content": content,
                    "thinking": thinking
                },
                "done": False
            }
            yield json.dumps(node) + "\n"

        # Final terminal chunk
        done_node = {
            "model": selected_model,
            "message": {
                "role": "assistant",
                "content": "",
                "thinking": ""
            },
            "done": True
        }
        yield json.dumps(done_node) + "\n"

    except Exception as e:
        logger.error(f"[GENERATOR ERROR]: {e}")
        error_node = {
            "error": "AI service error",
            "detail": str(e)
        }
        yield json.dumps(error_node) + "\n"

# ==========================================
# SMALL TALK GENERATOR
# ==========================================
def generate_small_talk(query: str, messages: list = None, model: str = None, **kwargs):
    logger.info(f"[GENERATOR] generate_small_talk: {query}")
    chat_messages = list(messages) if messages and isinstance(messages, list) and len(messages) > 0 else [{"role": "user", "content": query}]
    yield from stream_chat(chat_messages, model=model, **kwargs)

# ==========================================
# DIRECT GENERATOR
# ==========================================
def generate_direct(query: str, messages: list = None, model: str = None, **kwargs):
    logger.info(f"[GENERATOR] generate_direct: {query}")
    chat_messages = list(messages) if messages and isinstance(messages, list) and len(messages) > 0 else [{"role": "user", "content": query}]
    yield from stream_chat(chat_messages, model=model, **kwargs)

# ==========================================
# FACTUAL GENERATOR (WITH RAG CONTEXT)
# ==========================================
def generate_with_context(query: str, context: dict, messages: list = None, model: str = None, **kwargs):
    logger.info(f"[GENERATOR] generate_with_context: {query}")
    context_text = context.get("context", "") if isinstance(context, dict) else str(context)

    system_prompt = f"""Answer using the provided context.
If context does not contain the answer, answer normally if possible.

Retrieved Web Context:
{context_text}"""

    chat_messages = [{"role": "system", "content": system_prompt}]

    if messages and isinstance(messages, list) and len(messages) > 0:
        for msg in messages:
            if msg.get("role") != "system":
                chat_messages.append(msg)
    else:
        chat_messages.append({"role": "user", "content": query})

    yield from stream_chat(chat_messages, model=model, **kwargs)
