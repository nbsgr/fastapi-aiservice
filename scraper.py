import time,logging
from bs4 import BeautifulSoup

# =====================================================
# CONFIG
# =====================================================

MAX_TEXT_LENGTH = 15000

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# =====================================================
# CLEAN TEXT
# =====================================================

def clean_text(text:str):
    if not text:
        return ""
    #cleaning text
    cleaned_text=(" ".join(text.split()).strip())

    return cleaned_text

# =====================================================
# EXTRACT TEXT
# =====================================================

def extract_text(html:str):
    if not html:
        logger.warning("[SCRAPER] EMPTY HTML")
        return ""
    try:
        # try scraping the html with html.parser
        soup = BeautifulSoup(html, "html.parser")
        #junk tags to decompose
        junk_tags = ["script", "style","nav", "footer", "header",
            "aside","form","button","noscript", "svg","img","iframe"
        ]
        #decompose all the junk tags
        for tag in soup(junk_tags):
            tag.decompose()

        #Extract the text from the html content
        text=soup.get_text(" ",strip=True)
        logger.info(f"[SCRAPER] TEXT FROM BS4: {len(text)}")

        #clean the text using clean_text function
        text=clean_text(text)
        logger.info(f"[SCRAPER] TEXT FROM cleaned text: {len(text)}")

        #keep the text till max length only
        text=text[:MAX_TEXT_LENGTH]
        logger.info(f"[SCRAPER] FINAL TEXT: {len(text)}")

        return text
    except Exception as e:
        logger.error(f"[SCRAPER] EXCEPTION: {e}")
        return ""

# =====================================================
# SCRAPE PAGES
# =====================================================

def scrape_pages(crawl_result:dict):
    start_time=time.time()
    logger.info("===========SCRAPING STARTED===========")
    if not crawl_result.get("success"):
        logger.error(f"Failed to scrape pages{crawl_result}")
        return {
            "success": False,
            "documents":[],
            "count":0,
            "timeMs":0
        }
    pages = crawl_result.get("pages",[])
    if not pages:
        logger.error(f"Failed to scrape pages{crawl_result}")
        return {
            "success": False,
            "documents":[],
            "count":0,
            "timeMs":0
        }
    documents = []
    for page in pages:
        url=page.get("url", "")
        html=page.get("html","")
        logger.info(f"SCRAPING URL: {url}")
        text = extract_text(html)
        if not text:
            logger.error(f"[SCRAPER] FAILED TO EXTRACT TEXT: {url}")
            continue
        documents.append({
            "url":url,
            "text":text,
        })
        logger.info(f"[SCRAPER] ACCEPTED URL: {url}")
    logger.info(f"[SCRAPER] COMPLETE: COUNT: {len(documents)}")
    return {
        "success": True,
        "documents":documents,
        "count":len(documents),
        "timeMs":int((time.time()-start_time)*1000)
    }
