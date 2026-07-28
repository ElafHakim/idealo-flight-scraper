import csv
import time
import random
import scrapy
import asyncio
import json
from scrapy_playwright.page import PageMethod
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from flightscraper.items import FlightscraperItem
from datetime import date, timedelta, datetime, timezone
#from statistics import mean

class IdealoSpider(scrapy.Spider):
    name = "idealo"
    allowed_domains = ["flug.idealo.de"]

    PLAYWRIGHT_ABORT_REQUEST = lambda req: req.resource_type in [
        "image",
        "stylesheet",
        "media",
        "font"
    ]
    #   Diese überschreiben die Werte aus settings.py.
    custom_settings = {
        "PLAYWRIGHT_MAX_PAGES_PER_CONTEXT": 12,
        "DOWNLOAD_TIMEOUT": 60,
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 30000,# 
        "PLAYWRIGHT_DEFAULT_TIMEOUT": 30000,
        "DOWNLOAD_DELAY": 0.5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_MAX_DELAY": 20,
        "AUTOTHROTTLE_START_DELAY": 2.0, # war 3
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 12.0, # war 1
        "CONCURRENT_REQUESTS": 12,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 12,
        "COOKIES_ENABLED": True,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 1,
        "PLAYWRIGHT_ABORT_REQUEST": PLAYWRIGHT_ABORT_REQUEST,
    }
    DEPARTURE_START = date(2026, 6, 22)
    DEPARTURE_END = date(2026, 6, 28)
    WEEKDAYS_DE = ["Mo.", "Di.", "Mi.", "Do.", "Fr.", "Sa.", "So."]# WEEKDAYS_DE ist ein Klassenattribut
    #TARGET_DEPARTURE_DATE = "2026-06-06"
    #OUTBOUND_DATE = "06.06.2026"
    FLIGHT_CLASS_NAME = "economy"
    COMFORT_CLASS = "1"
    def __init__(self, batch_start=0, limit=1000, status_file=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch_start = int(batch_start)
        self.limit = int(limit)
        self.status_file = status_file or f"batch.txt"
    #Die 7 Abflugtage vom 22.06 bis 28.06 erzeugen und in die Formate umwandeln, die Idealo benötigt
    def iter_departure_dates(self):
        d = self.DEPARTURE_START
        while d <= self.DEPARTURE_END:
            yield d#Gib ein Datum zurück und merke dir die aktuelle Position. Beim nächsten Aufruf geht es mit dem nächsten Tag weiter.
            d += timedelta(days=1)
    #Idealo erwartet im Suchformular diese Form Mo. 22.06.26 
    def idealo_go_date(self, d):
        return f"{self.WEEKDAYS_DE[d.weekday()]} {d:%d.%m.%y}"
    #Wandelt das Datum in das Format um, das getResults.php erwartet date(2026, 6, 22) wird zu 22.06.2026
    def idealo_outbound_date(self, d):
        return d.strftime("%d.%m.%Y")
    #weil die JSON-Antwort von Idealo so aussieht {"start_date": "2026-06-22"} strftime formatiert n Datum in genau das Textformat, das du brauchst.
    def target_departure_date(self, d):
        return d.strftime("%Y-%m-%d")
    # -------------------------
    # START search requests
    # -------------------------
    def start_requests(self):

        routes = self.load_routes("flight_routes.csv")
        routes = routes[self.batch_start:self.batch_start + self.limit]
        blacklisted_iata = self.load_blacklisted_iata()

        # 1. Erst alte queued-Routen markieren
        #Wenn Route vorher bei queued hängen blieb,dann makeire sie problematic um beim nächsten Lauf zu skippen
        #queued_ids = self.load_first_queued_routes(limit=12)
        #for route in routes:
            #if route["uid"] in queued_ids:
                #self.mark_route_status(route, departure_date, "problematic")

        #2. Dann normale Verarbeitung starten
        completed_keys = self.load_completed_routes()
        #problematic_ids = self.load_problematic_routes()
        #no_searchid_found_ids = self.load_no_searchid_fount_routes()
        #service_unavailable_ids = self.load_service_unavailable_routes()

        for route in routes:
            for departure_date in self.iter_departure_dates():
                if (route["uid"], departure_date.isoformat()) in completed_keys:
                    continue
                if route["from"] == route["to"]:
                    self.mark_route_status(route, departure_date, "same_iata")
                    continue
                if route["from"] in blacklisted_iata or route["to"] in blacklisted_iata:
                    self.mark_route_status(route, departure_date, "blacklisted_iata")
                    continue

                # die Route wurde aus flight_routes.csv gelesen und für sie eine HTTP-POST-Request(Playwright-Request) an Scrapy übergeben 
                self.mark_route_status(route, departure_date, "queued")
                yield scrapy.FormRequest( #Flugsuche über das API Call search.php?action=search
                    #   intern passiert await page.goto("https://flug.idealo.de/search.php?action=search")
                    url="https://flug.idealo.de/search.php?action=search",# 
                    formdata={
                        "adults": "1",
                        "children": "0",
                        "infants": "0",
                        "comfortclass": self.COMFORT_CLASS,
                        "direct": "0",
                        "flexdates": "0",
                        "from": route["from"],
                        "to": route["to"],
                        "from_short": route["from"],
                        "to_short": route["to"],
                        "go_date":  self.idealo_go_date(departure_date),
                        #"go_date": "Sa. 06.06.26",
                        "type": "oneway",
                        "form_type": "simple",
                    },
                    callback=self.parse_search_response,# wird aufgerufen wenn die Suchseite von Idealo Flugsuche erfolgreich geladen wurde
                    errback=self.handle_search_error,# wird aufgerufen wenn die Suchseite von Idealo fehlgeschlagen  wurde
                    headers=self.search_headers(route),
                    cb_kwargs={
                        "route": route,
                        "departure_date": departure_date,
                        "seen_last": set(),
                        "seen_keys": set(),
                    },
                    meta={
                        "playwright": True,#    Playwright/Browser ladet diese post Request(search-request)
                        "playwright_include_page": True, # Scrapy-Playwright gib  mir das echte Playwright-Page-Objek
                    
                        "playwright_page_goto_kwargs": {
                        "wait_until": "domcontentloaded",
                        "timeout": 30000,
                        },
                        "playwright_page_methods": [
                            PageMethod("wait_for_timeout", 3000),# Dann hat Idealo mehr Zeit, startSearch.php oder getResults.php zu laden und somit search_id finden kann 
                            #PageMethod("wait_for_load_state", "networkidle")       
                        ],
                        "download_timeout": 60,
                        "handle_httpstatus_list": [503],# Falls ne 503-Response zurückkommt, soll trotzdem parse_search_response() aufgerufen werden 
                    },  
                    dont_filter=True,
                )


    def search_headers(self, route):# für die search request
        return {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://flug.idealo.de",
            "referer":"https://flug.idealo.de/",#flugroute/Frankfurt-FRA/New-York-JFK/
            "user-agent": self.get_user_agent(),
    }        

    # -------------------------
    # CSV LADEN
    # -------------------------
    def load_routes(self, csv_path):
        routes = []

        with Path(csv_path).open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                routes.append({
                    "uid": row["_id"].strip(),
                    "from": row["from"].strip().upper(),
                    "to": row["to"].strip().upper(),
                })

        return routes
    
    # wird aufgerufen wenn die Suchseite von Idealo geladen wurde und Responnse zurück ist
    async def parse_search_response(self, response, route, departure_date, seen_last, seen_keys,):

        self.mark_route_status(route, departure_date, "response_received")# Die Idealo-Suchseite wurde geladen.
        page = response.meta["playwright_page"]#  auf das Browser-Objekt greifen
        
        try: #   try finally sollte den playwright schritt schützen
            if response.status == 503:
                self.mark_route_status(route, departure_date, "503_service_unavailable")
                return  # geh zu fininally, keine Suchergebnisse -> keine normale Suche möglich
            tiny_id = response.url.rstrip("/").split("/")[-1]     #tiny_id wird aus der URL gelesen    
        #   alle geladenen Netzwerk-Ressourcen auslesen, dabei werden startSearch.php, getResults.php geladen
        #   Daraus extrahiere die echte searchid, die für weitere API-Aufrufe benötigt wird.
            resource_urls = await asyncio.wait_for(
                page.evaluate("""
                    () => performance.getEntriesByType('resource').map(e => e.name)
                """),
                timeout=10
            )
        except Exception as e:
            self.logger.error(
                f"PLAYWRIGHT PARSE ERROR | Route {route['uid']} | "
                f"{route['from']} -> {route['to']} | {e}"
            )
            #Playwright konnte die geladenenen Browser-Ressourcen nicht lesen
            self.mark_route_status(route, departure_date, "resource_extraction_error")
            return
     
        finally:
            try:# Bei erfolgreichem Ablauf die Seite(playwright-page) schließen
                await asyncio.wait_for(page.close(), timeout=5)#einzelne Playwright-Browser-Tab schließen

            except Exception as e:# falls Playwright beim Schließen der Page ein Problem hatt dann 
                self.mark_route_status(route, departure_date, "page_not_closed")
            
        search_id = None
         #  Nachdem die Suchseite geladen wurde, alle vom Browser geladenen Ressourcen auslesen
        for url in resource_urls:
            if "startSearch.php" in url or "getResults.php" in url:
                
                query = parse_qs(urlparse(url).query)
                 # searchid aus den geladenen Ressourcen (url) lesen - searchid in result-page finden
                search_ids = query.get("searchid")
                if search_ids:
                    search_id = search_ids[0]
                    break

        if not search_id:
            # Resourcen wurde gelesen, aber Idealo hat keine searchid geliefert 
            self.mark_route_status(route, departure_date, "no_searchid_found")
            return

        for request in self.start_api_request(
            route=route,
            departure_date=departure_date,
            seen_last=seen_last,
            seen_keys=seen_keys,
            tiny_id=tiny_id,
            search_id=search_id,  
        ):
            yield request

    # -------------------------
    # API START
    # -------------------------
    def start_api_request(self, route, departure_date, seen_last, seen_keys, tiny_id, search_id):

        params = {
            "searchid": search_id,       
            "tinyId": tiny_id,                         
            "last": "0",
            "formtype": "simple",
            "type": "oneway",
            "outboundAirportStartCode": route["from"],
            "outboundAirportArrivalCode": route["to"],
            "outboundDate": self.idealo_outbound_date(departure_date),
            #"outboundDate": self.OUTBOUND_DATE,
            "personCount": "1",
            "adults": "1",
            "infants": "0",
            "children": "0",
            "comfortclass": self.COMFORT_CLASS,
            "_": str(int(time.time() * 1000)),
        } 
        api_url = "https://flug.idealo.de/ajax/getResults.php?" + urlencode(params)

        yield scrapy.Request(
            url=api_url,
            callback=self.parse_api,
            errback=self.handle_api_error,     #jeder API-Request sollte eine Fehlerbehandlung bekommen.
            headers=self.api_headers(tiny_id),
            cb_kwargs={
                "route": route,
                "departure_date": departure_date,
                "seen_last": seen_last,
                "seen_keys": seen_keys,
                "tiny_id": tiny_id,
            },
            dont_filter=True,
        )
    # -------------------------
    # HEADERS
    # -------------------------

    def api_headers(self, tiny_id):
        return {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "referer": f"https://flug.idealo.de/ergebnis/{tiny_id}",
            "priority": "u=1, i",
            "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": self.get_user_agent(),
            "x-abgroup": "A",
            "x-requested-with": "XMLHttpRequest",
            #"cookie": " ",
        }

    def get_user_agent(self):
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.0.0 Safari/537.36"
        )

    # -------------------------
    # parst die API JSON RESPONSE von getResults.php, extrahiert Flugangebote, behandelt Pagination, setzt am Ende completed
    # -------------------------
    def parse_api(self, response, route, departure_date, seen_last, seen_keys, tiny_id,):
        #if response.status in [403, 429, 503]:
        try:
            data = response.json()# JSON Antwort kommt von der API getResults.php
        except Exception as e:
            self.logger.error(f"JSON ERROR | Route {route['uid']} | {route['from']} -> {route['to']} | {e}")
            self.mark_route_status(route, departure_date, "json_error")#    API-Antwort war kein gültiges JSON
            return
            

        
        try:
            offers = data.get("offers", [])
            #if offers:
                #print(json.dumps(offers[0], indent=2, ensure_ascii=False))
            for offer in offers:
                airport = offer.get("flight", {}).get("out", {}).get("airport", {})
                if airport.get("start_date") != self.target_departure_date(departure_date):  
                    continue
                item = self.extract_flight_data(offer, response.url, route)
                key = self.build_unique_flight_key(offer, item)

                if key in seen_keys:
                    continue

                seen_keys.add(key)
                yield item
            #Pagination-Block
            next_last = data.get("last")  # Zeiger(Cursor) auf die nächste Ergebnisseite und wird vollständig vom Idealo-Server bestimmt.
        
            if next_last and next_last not in seen_last:
                seen_last.add(next_last)

                next_url = self.replace_query_param(response.url, "last", str(next_last))
                next_url = self.replace_query_param(next_url, "_", str(int(time.time() * 1000)))

                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse_api,
                    errback=self.handle_api_error,# Bei jedem next_url Request ebenfalls:
                    headers=self.api_headers(tiny_id),
                    cb_kwargs={
                        "route": route,
                        "departure_date": departure_date,
                        "seen_last": seen_last,
                        "seen_keys": seen_keys,
                        "tiny_id": tiny_id,
                    },
                    dont_filter=True,
                )
   
            elif not next_last: # keine offers mehr dann Route als fertig markieren
                    self.mark_route_status(route, departure_date, "completed")  
            else:#Wenn next_last existiert, aber schon in seen_last ist, dann passiert nichts deswegen 
                self.mark_route_status(route, departure_date, "completed")

        except Exception as e:
            self.logger.error(
                f"PARSE_API ERROR | Route {route['uid']} | {route['from']} -> {route['to']} | {e}"
            )
            self.mark_route_status(route, departure_date, "parse_api_error")# Fehler beim Verarbeiten der gültigen JSON-RESPONSE_Daten
            return
        
    # -------------------------
    # ITEM
    # -------------------------
    def extract_flight_data(self, offer, url, route):
        item = FlightscraperItem()
        out = offer.get("flight", {}).get("out", {})
        airport = out.get("airport", {})
        airlines = out.get("airlines", [])
        offer_data = offer.get("offer", {})
        hand = offer_data.get("handBaggage", {})
        stops_airports = out.get("stops_airports", [])
        item["crawled_at"] = datetime.now(timezone.utc).isoformat()
        item["price"] = offer.get("offer", {}).get("total_price") or ""
        #item["airline_name"] = airlines[0].get("name") if airlines else ""
        #item["airline_id"] = airlines[0].get("code") if airlines else ""
        #item["flight_number"] = airlines[0].get("flight_number") if airlines else ""
        item["airline_name"] = ",".join(a.get("name", "") for a in airlines)
        item["airline_id"] = ",".join(a.get("code", "") for a in airlines)
        item["flight_number"] = ",".join(a.get("flight_number", "") for a in airlines)
        item["duration"] = airport.get("duration", "")
        item["stops"] = len(stops_airports)
        item["stop_airports"] = ",".join(s.get("code", "")for s in stops_airports)
        departure_time = airport.get("start_time", "")
        departure_date = airport.get("start_date", "")
        item["departure"] = f"{departure_date}T{departure_time}:00"
        arrival_time = airport.get("arrival_time")
        arrival_date = airport.get("arrival_date")
        item["arrival"] = f"{arrival_date}T{arrival_time}:00"
        item["from_str"] = airport.get("start_code", route["from"])
        item["to_str"] = airport.get("arrival_code", route["to"])
        item["flight_route_id"] = route["uid"]
        item["flight_class"] = self.FLIGHT_CLASS_NAME
        item["checked_baggage_included"] = offer_data.get("baggage_included")
        item["carry_on_baggage_included"] = hand.get("included")
        item["carry_on_baggage_weight"] = hand.get("weight")
        item["carry_on_baggage_size"] = hand.get("size")
        item["personal_item_included"] = "unknown"

        return item

    # -------------------------
    # KEY
    # -------------------------
    def build_unique_flight_key(self, offer, item):
        out = offer.get("flight", {}).get("out", {})
        flightsteps = out.get("flightsteps", "")

        flight_numbers = tuple(
            airline.get("flight_number", "")
            for airline in out.get("airlines", [])
        )

        return (
            item["from_str"],
            item["to_str"],
            item["departure"],
            #item["departure_time"],
            item["duration"],
            flightsteps,
            flight_numbers,
        )

    # -------------------------
    # UTILS
    # -------------------------
    def replace_query_param(self, url, key, value):
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query[key] = [value]

        new_query = urlencode(query, doseq=True)

        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )

    def mark_route_status(self, route, departure_date, status):

        path = Path(self.status_file)
        uid = route["uid"]
        key = f"{uid},{departure_date},{route['from']},{route['to']}"
   
        if not path.exists():
            with path.open("w", encoding="utf-8") as f:
                f.write(f"{key},{status}\n")
            return

        lines = path.read_text(encoding="utf-8").splitlines()
        updated = False

        for i, line in enumerate(lines):
            if line.startswith(f"{key},"):
                lines[i] = line + f",{status}"
                updated = True
                break

        # Route noch nicht vorhanden
        if not updated:
            lines.append(f"{key},{status}")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


    def handle_api_error(self, failure):
        route = failure.request.cb_kwargs["route"]
        departure_date = failure.request.cb_kwargs["departure_date"]

        self.logger.error(
            f"API ERROR | Route {route['uid']} | "
            f"{route['from']} -> {route['to']} | "
            f"{failure.value}"
    )
        self.mark_route_status(route, departure_date, "api_error")


    async def handle_search_error(self, failure):
        route = failure.request.cb_kwargs["route"]
        departure_date = failure.request.cb_kwargs["departure_date"]
        error_text = str(failure.value)
        self.logger.error( f"SEARCH ERROR | Route {route['uid']} | {route['from']} -> {route['to']} | {error_text}")
        #page=Browser-Tab von Playwright schließen, wenn beim Laden der Suchseite ein Fehler passiert.
        page = failure.request.meta.get("playwright_page")
        if page:
            try:
                await asyncio.wait_for(page.close(), timeout=5)#    playwright-page schließen

            except Exception:
                pass
         # Temporäre Playwright-/Browser-Probleme
        if "Timeout" in error_text:#error_text enthält Page.goto: Timeout 30000ms exceeded. ....
            #Playwright konnte im Moment die Suchseite nicht rechtzeitig laden, später kann es funktioneiren
            self.mark_route_status(route, departure_date, "Playwright_Timeout")
            return

        if "Page crashed" in error_text:
            self.mark_route_status(route, departure_date, "page_crashed")
            return

        if "Connection closed" in error_text:
            self.mark_route_status(route, departure_date, "connection_closed")
            return
        #Playwright wollte neuen Browser-Tab/Page erzeugen, aber Chromium/der Driver war gerade instabil oder schon teilweise geschlossen.
        if "Target.createTarget" in error_text:
            self.mark_route_status(route, departure_date, "target_create_target")
            return
        #else
        self.mark_route_status(route, departure_date, "search_error")
    
    def load_problematic_routes(self):
        path = Path(self.status_file)
        if not path.exists():
            return set()

        problematic_ids = set()

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")

                if len(parts) < 4:
                    continue

                uid = parts[0]
                last_status = parts[-1]

                if last_status == "problematic":
                    problematic_ids.add(uid)

        return problematic_ids 
    
    def load_no_searchid_fount_routes(self):
        path = Path(self.status_file)
        if not path.exists():
            return set()

        no_searchid_found_ids = set()

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")

                if len(parts) < 4:
                    continue

                uid = parts[0]
                last_status = parts[-1]

                if last_status == "no_searchid_found":
                    no_searchid_found_ids.add(uid)

        return no_searchid_found_ids
    
    def load_completed_routes(self):
        path = Path(self.status_file)

        if not path.exists():
            return set()

        completed_keys = set()

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")

                if len(parts) < 5:
                    continue

                uid = parts[0]
                departure_date = parts[1]
                last_status = parts[-1]

                if last_status == "completed":
                    completed_keys.add((uid, departure_date))

        return completed_keys 

    def load_service_unavailable_routes(self):
        path = Path(self.status_file)

        if not path.exists():
            return set()

        service_unavailable_ids = set()

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")

                if len(parts) < 4:
                    continue

                uid = parts[0]
                last_status = parts[-1]

                if last_status == "503_service_unavailable":
                    service_unavailable_ids.add(uid)

        return service_unavailable_ids 
    
    def load_first_queued_routes(self, limit=12):
        path = Path(self.status_file)

        if not path.exists():
            return set()

        queued_ids = []

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")

                if len(parts) < 4:
                    continue

                uid = parts[0]
                last_status = parts[-1]

                if last_status == "queued":
                    queued_ids.append(uid)

                if len(queued_ids) >= limit:
                    break

        return set(queued_ids)
    
    def load_blacklisted_iata(self):
        path = Path("blacklisted_iata_for_idealo.txt")

        if not path.exists():
            return set()

        return {
            line.strip().upper()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    