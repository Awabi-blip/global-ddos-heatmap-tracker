# Design Document 
by Muhammad Awab

# The Project
A tool to fetch, enrich, and store abusive IP addresses using AbuseIPDB and GeoIP2.

## Represnetation

``` Python
AbuseIPDB -> Server (FastAPI) -> Json Dump -> Json Read -> Transformation using GeoIP2 -> Into Database ( PostgreSQL ) -> Out of Database -> Server -> Frontend
```


## Scope
The purpose of this application is to provide a representative analysis of abusiveIP logs by fetching them from a popular abuse log API which is the **AbuseIPDB**, populating it with more data which was made possible thanks to the amazing project of MaxMind in **Geoip2 database**

The application takes JSON data from the API call, transforms it to contain more information, and be sent as a JSON to the frontend, which can then make use of that processed data to map **Abusive IP addresses** on a globe using a library like react globe.

## The Data Transformation
The data that we fetch from the API looks something like this:

```json

        {"ipAddress": "2.57.122.177", 
        "countryCode": "RO", 
        "abuseConfidenceScore": 100, 
        "lastReportedAt": "2026-02-12T06:17:02+00:00"}
        *10k items (in one api call)
````

### Extraction

The extraction process handles the API requests and authentication as follows:

```python
# Map out the skeleton of the API call
API_KEY: str = os.getenv('ABUSE_ipdb_API_KEY')
URL: str = 'https://api.abuseipdb.com/api/v2/blacklist'

# HTTP headers checked by the API for authentication
HEADERS: dict[str,str] = {
    'Accept': 'application/json',
    'Key': API_KEY
}

# Parameters that define what kind of data you want,
# confidenceMinimum set to 100 means only show me the IPs with a
# 100% confirmation of abuse, and limit set to 10k, which is the highest
# you can fetch in one call, if you want less data, you can decrease the limit,
# but you can't go higher than 10k.

PARAMS: dict[str, str] = {
    'confidenceMinimum': '100',
    'limit': '10000'
}

async with httpx.AsyncClient() as client:
    r: httpx.Response = await client.get(url=URL, headers=HEADERS, params= PARAMS)
        
    if r.status_code == 200:
        raw_data = r.json()

```
- You can get your API_KEY from this URL: 
https://www.abuseipdb.com/account/api
go to the page and scroll down a bit and you can see this option to create your API Key
<img width="1400" height="202" alt="image" src="https://github.com/user-attachments/assets/0559f51c-898d-4e55-9d2b-5f2f234b7970" />
Create the key and paste it in  a .env file.

It will look something like this:
```.env
ABUSE_ipdb_API_KEY=your_key_here
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

### Dumping the json in a .json file:
The **raw_data** variable now has a list of 10K ip_addresses, if you are on a free account, you will only get 5 daily calls, so you must treat the data with safety, dump it in a .json file, with this line of code:
``` Python
# quickly save the data in-case power goes out
# use write to overwrite previously written data
with open('data.json', 'w') as f:
    json.dump(raw_data, f)
```
- This will immediately dump the data into a file, since the data is only 2mb, this is affordable, it is slightly redundant because the optimal approach should be to store to the database correctly, my reason here to dump it into a local .json file was because I needed to dump it right after fetching it, the database insertion could take time and additionally, in my work flow, the data.json file always stores the only the last fetched data, and because it is opened for **write** and not **append** it stores only the new piece of data everytime, discarding the old one, because that functionality is leveraged to the **database** ofcourse, so in conclusion of these reasons, 
to secure a volatile state in data fetching, a local dump, based on the size of the fetched data **(2mb)**, made sense.

### Transformation
The API fetch gives us enough information to map those IP addresses and get more information about them.

Know the famous advice "keep your IP safe or else you can be tracked", we are going to use that exact phenomenon to map these IP addresses to a physical location, though not precisely accurate because the database we are using maps the IP addresses to the city first, and then returns the location of that city, but it is enough for my project.
The database we are using is the **GeoIp2 database provided by MaxMind**, and icing on the cake it has a python module!

The database takes an IP address and can return multiple pieces of information about it, learn more about the database here:
- https://www.maxmind.com/en/geoip-databases

To get started you will be downloading their latest database, called the 'GeoLite2-City.mmdb' directly into your computer from their website check here:
- https://dev.maxmind.com/geoip/geolite2-free-geolocation-data/

and open it with their module reader (more on this down)

Once downloaded, import the module with this code:
```Python
import geoip2.database
```
Then you can define a reader object and read the data from it, by giving it an IP address to query by:
```Python
with geoip2.database.Reader('GeoLite2-City.mmdb') as ip_reader:
```
After this you can query the database with an IP Address like this:
```Python
ip_information: object = ip_reader.city(ip_address)
```
It would return a city object, for that IP address, which we can then use to map it onto a phyiscal city and get that city's latitude and longitude like this:

```Python
latitude: float = ip_information.location.latitude
d['latitude'] = latitude

longitude: float = ip_information.location.longitude     
d['longitude'] = longitude      
```
Note that the database can return an 

```Python
    geoip2.errors.AddressNotFoundError
```
which is why we wrap our entire block of code in a ```try...except block```

```Python
def transform_data(raw_data : list[dict[str,Any]]) -> list[dict[str,Any]]:
    with geoip2.database.Reader('GeoLiteGe2-City.mmdb') as ip_reader:

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

```

I also want to bring your attention to a method I used to keep my app functioning while performing this CPU intensive transformation, the use ``` asyncio.to_thread ``` to offload a synchronous library (GeoIP2) into an asynchronous thread.

``` Python 

transformed_data: list[dict[str,Any] = await asyncio.to_thread(transform_data, raw_data=raw_data)

```

The way it works is that C libraries (yes GeoIP2) is a C library, not the database, but the library we imported that provides the functions (both are different if you are confused, note the library is a python module, while the database is something you'd download from the MaxMind website (link above) and store it in your local machine or cloud), so the way C libraries work is some of them (GeoIP2, numpy, pandas) unlock the GIL and allow multi_processing to happen, so by loading this operation into another async thread, I get 2 in 1 things, a multi threaded transformer function that also does not block the main thread, tho when I call the python native code i.e ``` d['latitude'] = None ``` The GIL is again acquired to make this happen, so partial multi_processing, full async (async does not care about GIL), which is pretty fast!

### Load
The main thread waits for the data to be processed and then bulk_inserts it into the database.

Here's how how you can achieve it:

```Python
transformed_data: list[dict[str,Any]]= await asyncio.to_thread(transform_data, raw_data=raw_data)

which looks like:
{  
  "ip_address": "159.223.212.254",
  "country_code": "NL",
  "latitude": 52.3520,
  "longitude": 4.9392,
  "last_reported_at": "2026-02-11 14:17:01+05"
}

# Once the data is back, insert it into the database.
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

```

- The ON CONFLICT code checks if the IP Address exists in our Database from before (this can happen if 2 API calls return overlapping APIs, in which case we just update when they were last_reported_at).



executeMany_Sql:

```Python
async def executeMany_sql(sql: str, data: list[dict[str,any]]) -> Optional[list[dict[str,str]]]:
    try:
        async with await psycopg.AsyncConnection.connect(
            os.getenv("DATABASE_URL"),
            row_factory=dict_row,
        ) as connection:
            
            async with connection.transaction():
                async with connection.cursor() as cursor:
                    ## executemany used to process large datasets
                    await cursor.executemany(sql, data)
                    
                    if cursor.description:
                        result = await cursor.fetchall()
                    else:
                        result = None  
                    return result

    
    except Exception as e:
        print(f"Database Error: {e}")

```

- If your dataset is extremely large, a few gigabytes or more, consider using itertools.batched (it will chunk your data and spread the data insert into multiple database calls, because if the data exceeds your RAM, you won't be able to hold it in one python variable)
https://docs.python.org/3/library/itertools.html#itertools.batched


After the insert the data looks like this:
<img width="1490" height="221" alt="image" src="https://github.com/user-attachments/assets/72d18ea4-4988-4111-aa56-8de6abe64c54" />

## The Database Structure
<img width="1024" height="627" alt="image" src="https://github.com/user-attachments/assets/05ddff22-13c7-4058-98fb-88b9d21db84e" />
- Generated Through https://sqlflow.gudusoft.com/#/ and dark modded through Nano Banana 2 
### Relationships
```SQL
countries have a one to many relationship with abusive_ips
```
- Which means that one country can appear multiple times in the abusive_ips table, but each abusive_ip only originates from one country

To put simply, think of it this way; how many countries does one Ip Address refer to? Obviously one, as IP Address maps to a physical address, whilst one country can have many physical addresses, because geographically countries have large areas, every single tile in that country can point to a different address. That's how one country can have multiple Ip Addresses, but that one Ip Address will only be unique to that country and no other country as the geographic point that Ip represents, can only belong to one country. One piece of land.

### Datatypes
**Country Codes**:
```SQL
char(2) for country_code (PK,JP,PS)

char(3) country_code_3 (PAK,JPN,PSE)

country_code : represents the ISO Alpha 2 codes.

country_code_2 : represents the ISO Alpha 3 codes.
```

**Latitude and Longitude**:
```SQL
latitude DECIMAL(10,7) CHECK (latitude >= -90 AND latitude <= 90)
longitude DECIMAL(11,7) CHECK (longitude >= -180 AND longitude <= 180)

The check to ensure that a latitude is between -90 and 90
and a longitude is beteen -180 to 180
ensures that the values being inserted into the database, does actually map onto Earthly locations (a latitude can only be from -90 to 90 and a longitude can only be from -180 to 180)

DECIMAL(10,7) which leaves room for 7 digits after decimal point and 3 integers. The maximum Geoip2 returns is 4 decimal places, but making it up to 7 is better because some real world scenarios can go up to 6 or 7 decimal points. 

If strictly aligned to GeoIp2 you are safe with (7,4).

Note that in postgreSQL the syntax is like (how many digits before decimal, how many digits after decimal).
```



