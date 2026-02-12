import geoip2.database
from db import script_sql,executeMany_sql
import asyncio
import httpx
import json
import os
from datetime import datetime
import time     
from dotenv import load_dotenv
import sys

load_dotenv()


API_KEY: str = os.getenv('ABUSE_ipdb_API_KEY')
URL: str = 'https://api.abuseipdb.com/api/v2/blacklist'

HEADERS: dict[str,str] = {
    'Accept': 'application/json',
    'Key': API_KEY
}

PARAMS: dict[str, str] = {
    'confidenceMinimum': '100',
    'limit': '10000'
}

async def load_data() -> None:
    global API_KEY, URL, HEADERS

    async with httpx.AsyncClient() as client:
        r: httpx.Response = await client.get(url=URL, headers=HEADERS, params= PARAMS)
        
    if r.status_code == 200:
        raw_data = r.json()
        # quickly save the data in-case power goes out
        # use write to overwrite previously written data
        with open('data.json', 'w') as f:
            json.dump(raw_data, f)
        # r stays as the newly fetched data
    else:
        # if nothing was fetched, use the default/last store
        # before app goes live, there would be data in data.json{} always
        # so open it, or the last save
        with open('data.json', 'r') as f:
            raw_data = json.load(f) 

    transformed_data: list[dict[str,Any]]= await asyncio.to_thread(transform_data, raw_data=raw_data)
    sql : str = """ 
        INSERT INTO abusive_ips 
        (ip_address, country_code,
        latitude, longitude, last_reported_at) 
        
        VALUES (%(ipAddress)s, %(countryCode)s, 
        %(latitude)s, 
        %(longitude)s,
        %(lastReportedAt)s)

        ON CONFLICT (ip_address)
        DO UPDATE SET
            last_reported_at = EXCLUDED.last_reported_at

    """    
    await executeMany_sql(sql, transformed_data)

    return

def transform_data(raw_data : list[dict[str,Any]]) -> list[dict[str,Any]]:
    with geoip2.database.Reader('GeoLite2-City.mmdb') as ip_reader:

        for d in raw_data['data']:
            ip_address: str = d.get("ipAddress")
            try:
                # get the ip information from the reader, returns an object with 
                # certain methods
                ip_information: object = ip_reader.city(ip_address)
                
                # get latitude and longitude from the ip_reader instance
                latitude: float = ip_information.location.latitude
                d['latitude'] = latitude
                
                longitude: float = ip_information.location.longitude     
                d['longitude'] = longitude      
            
            except geoip2.errors.AddressNotFoundError:
                d['latitude'] = None
                d['longitude'] = None
        
    return raw_data['data']

asyncio.run(load_data())



            

        




        

        
        
        

