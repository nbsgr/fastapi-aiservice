# ==========================================
# INTENT PROCESSOR
# ==========================================
import logging
from text_search import search_web
from crawler import crawl_urls
from scraper import scrape_pages
from rag import retrieve_context
from generator import generate_small_talk, generate_direct, generate_with_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# ==========================================
# PROCESS INTENT AND ROUTE TO GENERATOR
# ==========================================
def intent_processing(query: str, intent: str, messages: list = None, model: str = None, **kwargs):
    logger.info(f"======= INTENT PROCESSING STARTED: {intent} =======")

    if intent == "SMALL_TALK":
        yield from generate_small_talk(query, messages, model=model, **kwargs)
        return

    elif intent == "DIRECT":
        yield from generate_direct(query, messages, model=model, **kwargs)
        return

    elif intent == "WEB_SEARCH":
        logger.info("[PIPELINE] STARTING WEB SEARCH")
        search_result = search_web(query)
        crawl_result = crawl_urls(search_result)
        scrape_result = scrape_pages(crawl_result)
        context = retrieve_context(query, scrape_result)

        yield from generate_with_context(
            query,
            context,
            messages,
            model=model,
            **kwargs
        )
        return

    logger.warning(f"[INTENT] UNKNOWN INTENT={intent}, falling back to DIRECT")
    yield from generate_direct(query, messages, model=model, **kwargs)
