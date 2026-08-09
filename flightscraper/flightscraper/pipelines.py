# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
#from itemadapter import ItemAdapter
import re
from datetime import datetime, timedelta
from flightscraper.items import FlightItem
#import dateparser

class FlightscraperPipeline:
    def process_item(self, item):
        new_item = FlightItem()
        duration_td = self.format_duration(item["duration"])
        #new_item = ()
        new_item["crawled_at"] = item.get("crawled_at", "")
        new_item['airline_name'] = item['airline_name']
        #new_item["airline_id"] = item.get("airline_id", "")
        new_item["airline_iata"] = item.get("airline_iata", "")
        new_item['price'] = self.format_price(item['price'])
        new_item["flight_class"] = item["flight_class"]
        #new_item["flight_number"] = item.get("flight_number", "")
        #new_item['duration'] = self.format_duration(item['duration'])# umwandlung #str()
        #new_item["duration"] = duration_td
        new_item["duration_seconds"] = int(duration_td.total_seconds())
        new_item["stops"] = item.get("stops")
        #new_item["stop_airports"] = item.get("stop_airports", "")
        #new_item["departure_time"] = item.get("departure_time", "")
        #new_item["departure_date"] = item.get("departure_date", "")
        new_item["departure"] = item.get("departure")
        #new_item["arrival_time"] = item.get("arrival_time", "")
        #new_item["arrival_date"] = item.get("arrival_date", "")
        new_item["arrival"] = item.get("arrival")
        new_item["flight_route_id"] = item.get("flight_route_id", "")
        new_item['from_iata'] = item['from_iata']
        new_item['to_iata'] = item['to_iata']
        new_item["carry_on_baggage_included"] = item.get("carry_on_baggage_included")
        new_item["checked_baggage_included"] = item.get("checked_baggage_included")
        new_item["additional_baggage"] = item.get("additional_baggage")
        new_item["baggage_info_text"] = item.get("baggage_info_text")
        #new_item["carry_on_baggage_weight"] = item.get("carry_on_baggage_weight")
        #new_item["carry_on_baggage_size"] = item.get("carry_on_baggage_size")
        new_item["personal_item_included"] = item.get("personal_item_included")
        new_item["remaining_seats"] = item.get("remaining_seats")

        #print("\n==========================================")
        #print(dict(new_item))

        return new_item
    
    #def format_departure_time(self, departure_date: str, departure_time: str) -> datetime:
        #combined_str = f"{departure_date} {departure_time}"
        #result = dateparser.parse(combined_str, languages=['de'])
        #if result is None:
            #result = datetime.min
        #return result

    
    def format_duration(self, duration):
        if not duration:
            return timedelta(0)

        duration = str(duration).strip()

        hours = 0
        minutes = 0

        m = re.search(r'(\d+)\s*h', duration, re.I)
        if m:
            hours = int(m.group(1))

        m = re.search(r'(\d+)\s*min', duration, re.I)
        if m:
            minutes = int(m.group(1))

        m = re.search(r'(\d+)\s*Std', duration, re.I)
        if m:
            hours = int(m.group(1))

        m = re.search(r'(\d+)\s*Min', duration, re.I)
        if m:
            minutes = int(m.group(1))

        m = re.search(r'^(\d{1,3}):(\d{2})$', duration)
        if m:
            hours = int(m.group(1))
            minutes = int(m.group(2))

        return timedelta(hours=hours, minutes=minutes)
    
    def format_price(self, price_text):
        # Idealo liefert oft schon float-Werte
        if isinstance(price_text, (int, float)):
            return float(price_text)
        if price_text is None:
            return 0.0
        
        price_text = str(price_text)

        price_text = (
            price_text
            .replace("\xa0", "")
            .replace("€", "")
            .replace(" ", "")
            .strip()
        )

        # Deutsche Schreibweise: 2.965,99 -> 2965.99
        price_text = price_text.replace(".", "")
        price_text = price_text.replace(",", ".")

        try:
            return float(price_text)
        except ValueError:
            return 0.0
       
    
from pymongo import MongoClient

class SaveToMongoDBPipeline:

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.get("MDB_CONNECTION_STRING"))

    def __init__(self, connection_string):

        client = MongoClient(connection_string)
        db = client["web_mining"]
        self.coll = db["idealo_new"]
    
    def process_item(self, item):

        self.coll.insert_one({
            'crawled_at': item.get('crawled_at'),
            # Eckdaten zur Identifikation des Flugs
            'flight_route_id': item.get('flight_route_id'),
            'flight_class': item.get('flight_class'),
            'from_iata': item['from_iata'],
            'to_iata': item['to_iata'],
            'airline_name': item['airline_name'],
            #'airline_id': item.get('airline_id'),
            'airline_iata': item.get('airline_iata'),
            #'flight_number': item.get('flight_number'),
            'departure': item.get('departure'),
            'arrival': item.get('arrival'),
            'duration_seconds': item.get('duration_seconds'),
            # Bewertung des Angebots
            'price': item['price'],
            #'duration_str': self.format_timedelta_d_hm(item['duration']),
            #'duration': int(item['duration'].total_seconds()),
            'stops': item['stops'],
            'remaining_seats': item.get('remaining_seats'),
            #'stop_airports': item['stop_airports'],
            #'departure_date': item.get('departure_date'),
            #'departure_time': item.get('departure_time'),
            #'arrival_date': item.get('arrival_date'),
            #'arrival_time': item.get('arrival_time'),
            'personal_item_included': item.get('personal_item_included'),
            'carry_on_baggage_included': item.get('carry_on_baggage_included'),
            'checked_baggage_included': item.get('checked_baggage_included'),
            'additional_baggage': item.get('additional_baggage'),
            'baggage_info_text': item.get('baggage_info_text'),
            #'carry_on_baggage_weight': item.get('carry_on_baggage_weight'),
            #'carry_on_baggage_size': item.get('carry_on_baggage_size'),

    
        })
        return item

    #def format_timedelta_d_hm(self, td: timedelta) -> str:
        #days = td.days
        #total_seconds = td.seconds  # remainder after days

        #hours, remainder = divmod(total_seconds, 3600)
        #minutes = remainder // 60

        #return f"{days}:{hours:02}:{minutes:02}"