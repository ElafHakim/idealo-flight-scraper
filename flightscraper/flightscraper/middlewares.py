3# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class FlightscraperSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    async def process_start(self, start):
        # Called with an async iterator over the spider start() method or the
        # matching method of an earlier spider middleware.
        async for item_or_request in start:
            yield item_or_request

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class FlightscraperDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


from urllib.parse import urlencode
from random import randint
import requests

class ScrapeOpsFakeBrowserHeaderAgentMiddleware:
    #ScrapeOps liefert Headers  oder (liefert leere Liste oder crasht dann Fallback setzen)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def __init__(self, settings):
        self.scrapeops_api_key = settings.get('SCRAPEOPS_API_KEY')
        self.scrapeops_endpoint = settings.get('SCRAPEOPS_FAKE_BROWSER_HEADER_ENDPOINT', 'http://headers.scrapeops.io/v1/browser-headers') 
        self.scrapeops_fake_browser_headers_active = settings.get('SCRAPEOPS_FAKE_BROWSER_HEADER_ENABLED', True)
        self.scrapeops_num_results = settings.get('SCRAPEOPS_NUM_RESULTS')
        self.headers_list = []
        self._get_headers_list()
        self._scrapeops_fake_browser_headers_enabled()

    def _get_headers_list(self):

        ####################
        # Fallback einbauen 
        fallback_headers = [
            
            {
                "accept-language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                "sec-fetch-user": "?1",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-ch-ua-platform": '"Windows"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "user-agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/147.0.0.0 Safari/537.36"
                ),
                "upgrade-insecure-requests": "1",
            }

        ]
        if not self.scrapeops_api_key:
            self.headers_list = fallback_headers
            return
        
        payload = {'api_key': self.scrapeops_api_key}
        
        if self.scrapeops_num_results is not None:
            payload['num_results'] = self.scrapeops_num_results
        
        try:
            #timeout ergänzt Sonst kann requests.get() lange hängen:
            response = requests.get(self.scrapeops_endpoint, params=urlencode(payload), timeout=10)
        
            response.raise_for_status()##################
            json_response = response.json()
            self.headers_list = json_response.get('result', [])

        # hier prüfen 
            if not self.headers_list:
                self.headers_list = fallback_headers

        except requests.RequestException as e:
            print("=====================================================")
            print(f"ScrapeOps nicht erreichbar, benutze Fallback-Headers: {e}")
            self.headers_list = fallback_headers

        except ValueError as e:
            print("=====================================================")
            print(f"ScrapeOps JSON-Fehler, benutze Fallback-Headers: {e}")
            print("=====================================================")
            self.headers_list = fallback_headers



    def _get_random_browser_header(self):
        #Nach meinem geplanten Fallback ist len(self.headers_list) = 1. 
        random_index = randint(0, len(self.headers_list) - 1)
        return self.headers_list[random_index]
        #return random.choice(self.headers_list)


    def _scrapeops_fake_browser_headers_enabled(self):
        if self.scrapeops_api_key is None or self.scrapeops_api_key == '' or self.scrapeops_fake_browser_headers_active == False:
            self.scrapeops_fake_browser_headers_active = False
        else:
            self.scrapeops_fake_browser_headers_active = True
    
    def process_request(self, request):        
        random_browser_header = self._get_random_browser_header()

        request.headers['accept-language'] = random_browser_header.get('accept-language')
        request.headers['sec-fetch-user'] = random_browser_header.get('sec-fetch-user') 
        request.headers['sec-fetch-mod'] = random_browser_header.get('sec-fetch-mod') 
        request.headers['sec-fetch-site'] = random_browser_header.get('sec-fetch-site') 
        request.headers['sec-ch-ua-platform'] = random_browser_header.get('sec-ch-ua-platform') 
        request.headers['sec-ch-ua-mobile'] = random_browser_header.get('sec-ch-ua-mobile') 
        request.headers['sec-ch-ua'] = random_browser_header.get('sec-ch-ua') 
        request.headers['accept'] = random_browser_header.get('accept') 
        request.headers['user-agent'] = random_browser_header.get('user-agent') 
        request.headers['upgrade-insecure-requests'] = random_browser_header.get('upgrade-insecure-requests')