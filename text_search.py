import time
import logging
from ddgs import DDGS
from urllib.parse import urlparse
from urllib.parse import urlunparse

# =====================================================
# CONFIG
# =====================================================
MAX_RESULTS=15
MAX_TITLE_LENGTH=300
MAX_BODY_LENGTH=200
SEARCH_REGION="us-en"
SEARCH_SAFE="off"
DEBUG=True

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# =====================================================
# URL NORMALIZATION
# =====================================================

def normalize_url(url:str)->str:
    start_time=time.time()
    logger.info(f"Normalizing url: {url}")
    if not url:
        logger.info(f"No url provided {url}")
        logger.info(f"{int((time.time() - start_time) * 1000)}ms")
        return ""
    try:
        parsed_url = urlparse(url)
        logger.info(f"Parsed url: {parsed_url}")
        cleaned_url=parsed_url._replace(query="",fragment="")
        logger.info(f"Cleaned url: {cleaned_url}")
        logger.info(f"{int((time.time() - start_time) * 1000)}ms")
        normalized_url=str(urlunparse(cleaned_url))
        return normalized_url
    except Exception as e:
        logger.error(f"Exception: {e}")
        return url.strip()

# =====================================================
# URL VALIDATION
# =====================================================
def is_url_valid(url:str)->bool:
    if not url:
        return False
    try:
        parsed_url = urlparse(url)
        logger.info(f"Parsed url: {parsed_url}")
        if parsed_url.scheme in ["http","https"] and parsed_url.netloc:
            logger.info(f"Parsed url scheme: {parsed_url.scheme}")
            logger.info(f"Parsed url netloc: {parsed_url.netloc}")
            return True
        else:
            return False
    except Exception as e:
        logger.info(f"{url}")
        logger.error(f"Exception: {e}")

        return False

# =====================================================
# DOMAIN EXTRACTION
# =====================================================
def domain_extraction(url:str)->str:
    if not url:
        return ""
    try:
        parsed_url = urlparse(url)
        logger.info(f"Parsed url: {parsed_url}")
        domain=parsed_url.netloc.lower().strip()
        logger.info(f"Domain: {domain}")
        return domain
    except Exception as e:
        logger.info(f"{url}")
        logger.error(f"Exception: {e}")
        return ""


# =====================================================
# SEARCH WEB
# =====================================================
def search_web(query:str,MAX_RESULTS:int=MAX_RESULTS):
    start_time = time.time()
    if not query or not query.strip():
        logger.warning(f"[SEARCH] Empty Query: {query}")
        return {
            "success": False,
            "error": "Empty Query",
            "results":[],
            "timeMs":0
        }
    query=query.strip()
    rows=[]
    seen_urls=set()
    domains=set()
    # =================================================
    # SEARCH
    # =================================================
    try:
        logger.info("=========WEB SEARCH STARTED==========")
        logger.info(f"[SEARCH CONFIG] "
                    f"SEARCH_REGION={SEARCH_REGION} "
                    f"SEARCH_SAFE={SEARCH_SAFE} "
                    f"max_results={MAX_RESULTS} "
                    f"MAX_TITLE_LENGTH={MAX_TITLE_LENGTH} "
                    )
        #python itself automatically creates and manages object with keyword
        with DDGS() as ddgs:
            results=ddgs.text(query,region=SEARCH_REGION,
                              safesearch=SEARCH_SAFE,
                              max_results=MAX_RESULTS,
                              )
            if results is None:
                logger.warning(f"[SEARCH] No results found for: {query}")
                results=[]
            else:
                results = list(results)
            logger.info(f"[SEARCH] Found {len(results)} results for {query}")

            for result in results:
                try:
                    title = result.get("title", "").strip()
                    url = result.get("href", "").strip()
                    body = result.get("body", "").strip()
                    logger.info("======================================")
                    logger.info(f"[TITLE] {title}")
                    logger.info(f"[URL] {url}")
                    logger.info(f"[BODY] {body[:100]}")
                    normalized_url=normalize_url(url)
                    logger.info(f"[NORMALISED URL] {normalized_url}")
                    if not is_url_valid(normalized_url):
                        logger.error(f"[INVALID URL] {normalized_url}")
                        continue
                    if normalized_url in seen_urls:
                        logger.info(f"[DUPLICATE URL] {normalized_url} already seen")
                        continue
                    seen_urls.add(normalized_url)
                    logger.info(f"[SEEN URLS] {seen_urls}")
                    domain=domain_extraction(normalized_url)
                    domains.add(domain)
                    logger.info(f"[SEEN DOMAINS] {domains}")
                    rows.append({"title": title[:MAX_TITLE_LENGTH],
                                 "url": normalized_url,
                                 "domain": domain,
                                 "body": body[:MAX_BODY_LENGTH],
                                  })
                    logger.info(f"[ACCEPTED] {normalized_url}")
                except Exception as e:
                    logger.error(f"[SEARCH ERROR] {e}")
                    continue
            logger.info(
                f"[SEARCH COMPLETE] "
                f"Accepted URLs={len(rows)} "
                f"Domains={len(domains)}"
                )

            return {
                "success": True,
                "query": query,
                "results": rows,
                "count": len(rows),
                "domains": list(domains),
                "timeMs": int((time.time() - start_time) * 1000)
            }
    except Exception as e:
        logger.error(f"[SEARCH ERROR] {e}")
        return {
            "success": False,
            "error": str(e),
            "results": [],
            "count": 0,
            "domains": [],
            "timeMs": int((time.time() - start_time) * 1000)
        }











