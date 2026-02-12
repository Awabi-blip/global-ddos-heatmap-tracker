from pydantic import BaseModel, TypeAdapter
from ipaddress import IPv4Address, IPv6Address
from db import script_sql

class AbusiveIp(BaseModel):
    ip_address: IPv4Address | IPv6Address
    latitude: float | None
    longitude: float | None

abusive_ips_adapter = TypeAdapter(list[AbusiveIp])


class AbusiveCountry(BaseModel):
    country_code : str
    attack_count : int

abusive_country_adapter = TypeAdapter(list[AbusiveCountry])



sql:str = """ SELECT ip_address, longitude, latitude 
              FROM abusive_ips
              ORDER BY last_reported_at
              LIMIT 10000
    """

rows = script_sql(sql)
validated_ips = abusive_ips_adapter.validate_python(rows)
json_abusive_ips = abusive_ips_adapter.dump_json(validated_ips)

