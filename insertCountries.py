import pycountry
from countryinfo import CountryInfo
import asyncio
import os
from dotenv import load_dotenv
import pprint
from db import executeMany_sql

all_countries: list[object] = list(pycountry.countries)
country_data: list[dict[str,any]] = []

async def insert_countries():
    for index, c in enumerate(all_countries):
        country_dict = {}
        country_object_for_lat_long: object = CountryInfo(c.alpha_2)
        
        try:
            latitude: float =  country_object_for_lat_long.latlng()[0]
            longitude: float = country_object_for_lat_long.latlng()[1]
        except KeyError:
            latitude = None
            longitude = None
        
        country_dict['numeric'] = c.numeric
        country_dict['country_code'] = c.alpha_2
        country_dict['country_code_3'] = c.alpha_3
        country_dict['name'] = c.name
        country_dict['latitude'] = latitude
        country_dict['longitude'] = longitude

        country_data.append(country_dict)
    sql = """
            INSERT INTO countries (numeric, country_code, country_code_3, name, latitude, longitude)
            VALUES (%(numeric)s, %(country_code)s, %(country_code_3)s, %(name)s, 
            %(latitude)s, %(longitude)s)
          """
    
    await executeMany_sql(sql, country_data)

asyncio.run(insert_countries())
