from datetime import datetime
import socket
import ssl
import time
import geoip2
import httpx


async def fetch_website_ip(session, url):
    website = f"https://www.{url}/"
    try:
        response = await session.get(website)
        ip = socket.gethostbyname(url)  # Example for fetching IP
        status = "Up" if response.status == 200 else "Down"
        return website, ip, status, response.status
    except Exception as e:
        return website, "IP Not Found", "Down", None
    
def get_geolocation(ip):
    try:
        with geoip2.database.Reader('GeoLite2-City.mmdb') as reader:
            response = reader.city(ip)
            return {
                "city": response.city.name,
                "country": response.country.name,
                "latitude": response.location.latitude,
                "longitude": response.location.longitude
            }
    except Exception as e:
        return {"error": str(e)}
    
def get_dns_resolution_time(domain):
    try:
        start_time = time.time()
        ip = socket.gethostbyname(domain)
        dns_time = time.time() - start_time
        return {"ip": ip, "dns_resolution_time": dns_time}
    except Exception as e:
        return {"error": str(e)}
    
async def get_http_headers(url):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.head(url)
            return response.headers
    except Exception as e:
        return {"error": str(e)}

def get_ssl_certificate_info(domain):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                
                # Extract relevant details
                issued_to = cert.get('subject', [])
                issuer = cert.get('issuer', [])
                not_before = datetime.strptime(cert['notBefore'], "%b %d %H:%M:%S %Y %Z")
                not_after = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")

                return {
                    "issued_to": issued_to,
                    "issuer": issuer,
                    "valid_from": not_before,
                    "valid_until": not_after
                }
    except Exception as e:
        return {"error": str(e)}
    

async def enrich_metadata(url):
    website = f"https://www.{url}/"
    session = httpx.AsyncClient()

    ip_info = await fetch_website_ip(session, url)
    dns_info = get_dns_resolution_time(url)
    ssl_info = get_ssl_certificate_info(url)
    headers = await get_http_headers(website)
    location_info = get_geolocation(ip_info["ip"])

    return {
        "ip_info": ip_info,
        "dns_info": dns_info,
        "ssl_info": ssl_info,
        "http_headers": headers,
        "geolocation": location_info,
    }