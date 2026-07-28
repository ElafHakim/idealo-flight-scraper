import asyncio
import scrapy
from pathlib import Path
from scrapy_playwright.page import PageMethod
from urllib.parse import urlparse, parse_qs


class ValidateIataSpider(scrapy.Spider):
    name = "validate_iata"
    allowed_domains = ["flug.idealo.de"]
    PLAYWRIGHT_ABORT_REQUEST = lambda req: req.resource_type in [
        "image",
        "stylesheet",
        "media",
        "font"
    ]
    custom_settings = {
        "PLAYWRIGHT_MAX_PAGES_PER_CONTEXT": 12,
        "DOWNLOAD_TIMEOUT": 60,
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 30000,# 
        "PLAYWRIGHT_DEFAULT_TIMEOUT": 30000,
        "DOWNLOAD_DELAY": 0.5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_MAX_DELAY": 20,
        "AUTOTHROTTLE_START_DELAY": 2.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 12.0,
        "CONCURRENT_REQUESTS": 12,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 12,
        "COOKIES_ENABLED": True,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 1,
        "PLAYWRIGHT_ABORT_REQUEST": PLAYWRIGHT_ABORT_REQUEST,
    }

    TEST_IATA_FILE = "test_iata.txt"
    STATUS_FILE = "iata_validation_status.txt"

    TEST_PARTNER = "FRA"
    GO_DATE = "Mo. 22.06.26"

    def start_requests(self):
        iata_codes = self.load_iata_from_file(self.TEST_IATA_FILE)

        self.logger.info(f"IATA-Codes zum Testen: {len(iata_codes)}")

        for iata in sorted(iata_codes):
            if iata == self.TEST_PARTNER:
                continue

            yield self.build_test_request(
                iata=iata,
                from_code=iata,
                to_code=self.TEST_PARTNER,
                direction="from",
            )

            yield self.build_test_request(
                iata=iata,
                from_code=self.TEST_PARTNER,
                to_code=iata,
                direction="to",
            )

    def load_iata_from_file(self, filename):
        path = Path(filename)

        if not path.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {filename}")

        return {
            line.strip().upper()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

    def build_test_request(self, iata, from_code, to_code, direction):
        return scrapy.FormRequest(
            url="https://flug.idealo.de/search.php?action=search",
            formdata={
                "adults": "1",
                "children": "0",
                "infants": "0",
                "comfortclass": "1",
                "direct": "0",
                "flexdates": "0",
                "from": from_code,
                "to": to_code,
                "from_short": from_code,
                "to_short": to_code,
                "go_date": self.GO_DATE,
                "type": "oneway",
                "form_type": "simple",
            },
            callback=self.parse_validation_response,
            errback=self.handle_error,
            headers=self.search_headers(),
            cb_kwargs={
                "iata": iata,
                "from_code": from_code,
                "to_code": to_code,
                "direction": direction,
            },
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_goto_kwargs": {
                    "wait_until": "domcontentloaded",
                    "timeout": 30000,
                },
                "playwright_page_methods": [
                    PageMethod("wait_for_timeout", 3000),
                ],
                "handle_httpstatus_list": [503],
            },
            dont_filter=True,
        )

    async def parse_validation_response(self, response, iata, from_code, to_code, direction):
        page = response.meta["playwright_page"]

        if response.status == 503:
            self.write_status(iata, direction, from_code, to_code, "503_service_unavailable")
            await self.safe_close_page(page)
            return

        try:
            resource_urls = await asyncio.wait_for(
                page.evaluate("""
                    () => performance.getEntriesByType('resource').map(e => e.name)
                """),
                timeout=10,
            )
        except Exception:
            self.write_status(iata, direction, from_code, to_code, "resource_extraction_error")
            await self.safe_close_page(page)
            return

        await self.safe_close_page(page)

        search_id = None

        for url in resource_urls:
            if "startSearch.php" in url or "getResults.php" in url:
                query = parse_qs(urlparse(url).query)
                search_ids = query.get("searchid")

                if search_ids:
                    search_id = search_ids[0]
                    break

        if search_id:
            self.write_status(iata, direction, from_code, to_code, "searchid_found")
        else:
            self.write_status(iata, direction, from_code, to_code, "no_searchid_found")

    async def handle_error(self, failure):
        iata = failure.request.cb_kwargs["iata"]
        from_code = failure.request.cb_kwargs["from_code"]
        to_code = failure.request.cb_kwargs["to_code"]
        direction = failure.request.cb_kwargs["direction"]

        error_text = str(failure.value)

        page = failure.request.meta.get("playwright_page")
        if page:
            await self.safe_close_page(page)

        if "Timeout" in error_text:
            status = "timeout"
        elif "Page crashed" in error_text:
            status = "page_crashed"
        elif "Connection closed" in error_text:
            status = "connection_closed"
        elif "Target.createTarget" in error_text:
            status = "target_create_target"
        else:
            status = "search_error"

        self.write_status(iata, direction, from_code, to_code, status)

    async def safe_close_page(self, page):
        try:
            await asyncio.wait_for(page.close(), timeout=5)
        except Exception:
            pass

    def write_status(self, iata, direction, from_code, to_code, status):
        path = Path(self.STATUS_FILE)

        with path.open("a", encoding="utf-8") as f:
            f.write(f"{iata},{direction},{from_code},{to_code},{status}\n")

        self.logger.info(
            f"IATA TEST | {iata} | {direction} | {from_code}->{to_code} | {status}"
        )

    def search_headers(self):
        return {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://flug.idealo.de",
            "referer": "https://flug.idealo.de/",
            "user-agent": self.get_user_agent(),
        }

    def get_user_agent(self):
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.0.0 Safari/537.36"
        )