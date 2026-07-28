# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class FlightscraperItem(scrapy.Item):
   crawled_at = scrapy.Field()
   airline_name = scrapy.Field()
   airline_id = scrapy.Field()
   price = scrapy.Field()
   duration = scrapy.Field()
   duration_seconds = scrapy.Field()
   stops=scrapy.Field()
   stop_airports=scrapy.Field()
   #departure_time = scrapy.Field()
   #departure_date = scrapy.Field()
   #arrival_time = scrapy.Field()
   #arrival_date = scrapy.Field()
   departure = scrapy.Field()
   arrival = scrapy.Field()
   from_str = scrapy.Field()
   to_str = scrapy.Field()
   flight_route_id = scrapy.Field()
   flight_class = scrapy.Field()
   flight_number = scrapy.Field()
   checked_baggage_included = scrapy.Field()
   carry_on_baggage_included = scrapy.Field()
   carry_on_baggage_weight = scrapy.Field()
   carry_on_baggage_size = scrapy.Field()
   personal_item_included = scrapy.Field()

def serialize_duration(value):
   return str(value)

class FlightItem(scrapy.Item):
   crawled_at = scrapy.Field()
   airline_name = scrapy.Field()
   airline_id = scrapy.Field()
   price = scrapy.Field()
   duration = scrapy.Field(serializer=serialize_duration)
   duration_seconds = scrapy.Field()
   stops=scrapy.Field()
   stop_airports=scrapy.Field()
   #departure_time = scrapy.Field()
   #departure_date = scrapy.Field()
   #arrival_time = scrapy.Field()
   #arrival_date = scrapy.Field()
   departure = scrapy.Field()
   arrival = scrapy.Field()
   from_str = scrapy.Field()
   to_str = scrapy.Field()
   flight_route_id = scrapy.Field()
   flight_class = scrapy.Field()
   flight_number = scrapy.Field()
   checked_baggage_included = scrapy.Field()
   carry_on_baggage_included = scrapy.Field()
   carry_on_baggage_weight = scrapy.Field()
   carry_on_baggage_size = scrapy.Field()
   personal_item_included  = scrapy.Field()
   
