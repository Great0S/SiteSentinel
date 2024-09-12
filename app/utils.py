from datetime import datetime
import os
import socket
import ssl
import time
import ipinfo
import httpx


def get_geolocation(ip):
    try:
        token = os.getenv("IPINFO_TOKEN")
        handler = ipinfo.getHandler(access_token=token)
        if handler:
            details = handler.getDetails(ip)
            return details.all
    except Exception as e:
        return {"error": str(e)}
    
async def get_dns_info(domain):
    website = f"https://www.{domain}/"
    session = httpx.AsyncClient()
    try:
        response = await session.get(website)
        start_time = time.time()
        ip = socket.gethostbyname(domain)
        dns_time = time.time() - start_time
        status = "Up" if response.status_code == 200 else "Down"
        
        return {"ip": ip, "status": status, "status_code": response.status_code, "headers": response.headers, "dns_resolution_time": dns_time}
    except Exception as e:
        return {"error": str(e)}

async def get_ssl_certificate_info(domain):
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
    dns_info = await get_dns_info(url)
    ssl_info = await get_ssl_certificate_info(url)
    location_info = get_geolocation(dns_info.get("ip", ""))

    # DNS Information
    dns_data = {
        "ip": dns_info.get("ip", "IP Not Found"),
        "status": dns_info.get("status", "Unknown"),
        "status_code": dns_info.get("status_code", 0),
        "headers": dns_info.get("headers", {}),
        "dns_resolution_time": dns_info.get("dns_resolution_time", None)
    }

    # SSL Information
    ssl_data = {
        "ssl_issued_to": ssl_info.get('issued_to', [[["", ""]]])[0][0][1] if ssl_info.get('issued_to') else "Unknown",
        "ssl_issuer": [x[0][1] for x in ssl_info.get("issuer", [[["", ""]]])] if ssl_info.get("issuer") else ["Unknown"],
        "ssl_valid_from": ssl_info.get("valid_from", None),
        "ssl_valid_until": ssl_info.get("valid_until", None)
    }

    # Geolocation Information
    location_data = {
        "hostname": location_info.get('hostname', "Unknown"),
        "city": location_info.get('city', "Unknown"),
        "region": location_info.get('region', "Unknown"),
        "country": location_info.get('country', "Unknown"),
        "loc": location_info.get('loc', "Unknown"),
        "org": location_info.get('org', "Unknown"),
        "postal": location_info.get('postal', "Unknown"),
        "timezone": location_info.get('timezone', "Unknown"),
        "country_name": location_info.get('country_name', "Unknown"),
        "country_code": location_info.get('country_currency', {}).get('code', "Unknown"),
        "continent_name": location_info.get('continent', {}).get('name', "Unknown"),
        "continent_code": location_info.get('continent', {}).get('code', "Unknown"),
        "latitude": location_info.get('latitude', None),
        "longitude": location_info.get('longitude', None),
        "country_flag": location_info.get('country_flag_url', "Unknown")
    }

    # Combine all data into one dictionary
    data = {
        f"https://www.{url}/": {
            **dns_data,
            **ssl_data,
            **location_data
        }
    }

    return data
