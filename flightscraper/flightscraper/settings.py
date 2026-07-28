# Scrapy settings for flightscraper project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import sys
import asyncio


if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
BOT_NAME = "flightscraper"

SPIDER_MODULES = ["flightscraper.spiders"]
NEWSPIDER_MODULE = "flightscraper.spiders"

SCRAPEOPS_API_KEY = '889e8234-0d6c-49b0-8c79-f8389028abaa' # signup at https://scrapeops.io
SCRAPEOPS_FAKE_USER_AGENT_ENDPOINT = 'https://headers.scrapeops.io/v1/user-agents'
SCRAPEOPS_FAKE_USER_AGENT_ENABLED = True
SCRAPEOPS_NUM_RESULTS = 100

MDB_CONNECTION_STRING = 'mongodb://localhost:27017/?directConnection=true'
CRAWL_DATE='2026-04-09'
ROTATING_PROXY_LIST_PATH = './proxies.txt'

#FEEDS = {
#    'flights.json': {'format': 'json', 'overwrite': True}
#}

#PLAYWRIGHT_CONTEXTS = {
#    "persistent": {"user_data_dir": "/tmp/playwright_user_data"},
#}

ADDONS = {}

LOG_LEVEL = "INFO"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "asyncio": {
            "level": "CRITICAL",
        },
    },
}

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "flightscraper (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

#PLAYWRIGHT_CONTEXTS = {
#    "default": {
#        "viewport": {
#            "width": 1080,
#            "height": 10000,
#        },
#    },
#}

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# Concurrency and throttling settings
#CONCURRENT_REQUESTS = 32
#CONCURRENT_REQUESTS_PER_DOMAIN = 32
#DOWNLOAD_DELAY = 0

# Enable AutoThrottle
AUTOTHROTTLE_ENABLED = True

# Target concurrency
AUTOTHROTTLE_TARGET_CONCURRENCY = 16

# Delay behavior
AUTOTHROTTLE_START_DELAY = 0.1
AUTOTHROTTLE_MAX_DELAY = 5

# IMPORTANT: raise concurrency limits
CONCURRENT_REQUESTS = 32
CONCURRENT_REQUESTS_PER_DOMAIN = 16

# Optional but recommended
DOWNLOAD_DELAY = 0  # let AutoThrottle fully control it
AUTOTHROTTLE_DEBUG = False

PLAYWRIGHT_MAX_CONTEXTS = 1
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 16

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "flightscraper.middlewares.FlightscraperSpiderMiddleware": 543,    FlightscraperSpiderMiddleware is the classname in middlewares.py
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
#    "flightscraper.middlewares.FlightscraperDownloaderMiddleware": 543,
    #'flightscraper.middlewares.DynamicProxyMiddleware': 350,
    'flightscraper.middlewares.ScrapeOpsFakeBrowserHeaderAgentMiddleware': 400,
    #'rotating_proxies.middlewares.RotatingProxyMiddleware': 610,
    #'rotating_proxies.middlewares.BanDetectionMiddleware': 620,
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    "flightscraper.pipelines.FlightscraperPipeline": 300,
    "flightscraper.pipelines.SaveToMongoDBPipeline": 400,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"
