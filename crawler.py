import time,logging
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
HEADERS={
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
MAX_CRAWL_URLS = 3
REQUEST_TIMEOUT = 10
DEBUG = True

# =====================================================
# SESSION
# =====================================================

crawler_session=requests.Session()
crawler_session.headers.update(HEADERS)

# =====================================================
# HTML VALIDATION
# =====================================================

def is_html_valid(response):
    logger.info("[HTML VALIDATION]")
    #check the status already checks in fetch_page
    #just confirmation check again
    if response.status_code != 200:
        logger.error(f"[HTML] BAD STATUS:{response.status_code}")
        return False

    content_type =(response.headers.get("Content-Type","").lower())

    if "text/html" not in content_type:
        logger.error(f"[HTML] NOT HTML:{content_type}")
        return False

    if len(response.content) == 0:
        logger.error(f"[HTML] EMPTY RESPONSE:{content_type}")
        return False
    return True



# =====================================================
# FETCH PAGE
# =====================================================

def fetch_page(url:str):
    logger.info(f"fetching page {url}")
    try:
        response=crawler_session.get(url,timeout=REQUEST_TIMEOUT)
        logger.info(f"got response from {response.status_code}")
        #check status code of response
        if response.status_code != 200:
            logger.error(f"Error response from {response.status_code}")
            return None
        elif not is_html_valid(response):
            return None
        else:
            logger.info(f"Success response from {response.status_code}")
            return response.text

    except Exception as e:
        logger.error(f"[FETCH PAGE ERROR] {e}")
        return None

# =====================================================
# CRAWL URLS
# =====================================================

def crawl_urls(search_result:dict):
    start_time = time.time()
    pages=[]
    visited_urls=set()
    logger.info("==============CRAWLING STARTED==============")
    #check whether sucess=True or false
    if not search_result.get("success"):
        logger.error(f"[CRAWLER] Invalid search result")
        return {
            "success": False,
            "pages":[],
            "count":0,
            "timeMs":0
        }
    else:
        results=search_result.get("results",[])[:MAX_CRAWL_URLS]

        if not results:
            logger.error(f"[CRAWLER] No results found:{results}")
            return {
                "success": False,
                "pages": [],
                "count": 0,
                "timeMs": 0
            }
        else:
            logger.info(f"[CRAWLER] Found {len(results)} results")
            for result in results:
                url = result.get("url","").strip()
                if not url:
                    logger.warning(f"[CRAWLER] No url found:{result}")
                    continue
                if url in visited_urls:
                    logger.info(f"[CRAWLER] Duplicate URL:{url}")
                    continue
                visited_urls.add(url)
                logger.info(f"[CRAWLER] Visited URLs:{visited_urls}")

                #Call the fetch page function to get the ccontent
                html = fetch_page(url)
                if not html:
                    logger.warning(f"[CRAWLER] FAILED TO FETCH: {url},{html}")
                    continue
                logger.info(f"[CRAWLER] FETCH SUCCESS:{url}")
                pages.append({
                    "url":url,
                    "html":html,
                })
                logger.info(f"[CRAWLER] PAGE ADDED | TOTAL PAGES={len(pages)}")
                logger.info(f"[CRAWLER] PAGE | {url}")
                logger.info(f"[CRAWLER] TIME:{int((time.time()-start_time)*1000)}ms")
            logger.info(f"[CRAWLER] COMPLETED CRAWLING FOUND {len(pages)} pages")
            return {
                "success": True,
                "pages": pages,
                "count": len(pages),
                "timeMs": int((time.time()-start_time)*1000)
            }







