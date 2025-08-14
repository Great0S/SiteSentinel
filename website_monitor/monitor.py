from database import db
from ssl_monitor import SSLMonitor
from health_scoring import EnhancedHealthScorer, HealthScorer
from dns_monitor import dns_monitor
from alert_system import alert_manager, AlertMessage, AlertSeverity, AlertType
import requests
import asyncio
import pandas as pd
import aiohttp
import smtplib
import logging
import os
import json
import socket
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from threading import Thread
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import database


# Constants
EMAIL_SERVER = os.getenv("EMAIL_SERVER")
EMAIL_PORT = os.getenv("EMAIL_PORT")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
ERROR_THRESHOLD = 3
RETRY_COUNT = 3
METADATA_FILE = "metadata.json"

# Logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Load websites from database on startup
websites = db.get_all_websites()


def sync_websites_to_db():
    """Synchronize in-memory websites to database with error handling and batching"""
    if not websites:
        return

    success_count = 0
    error_count = 0

    # Batch all updates in a single transaction for better performance
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            for url, data in websites.items():
                try:
                    cursor.execute('''
                        UPDATE websites 
                        SET status = ?, ip_address = ?, status_code = ?, response_time = ?,
                            error_count = ?, last_check = ?, ssl_info = ?, dns_info = ?,
                            health_score = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE url = ?
                    ''', (
                        data.get('status'),
                        data.get('ip'),
                        data.get('status_code'),
                        data.get('response_time'),
                        data.get('error_count', 0),
                        data.get('last_check'),
                        json.dumps(data.get('ssl_info', {})),
                        json.dumps(data.get('dns', {})),
                        json.dumps(data.get('health_score', {})),
                        url
                    ))
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logging.error(f"Failed to sync {url} to database: {e}")

            conn.commit()
            logging.info(
                f"Database batch sync: {success_count} successful, {error_count} failed")

    except Exception as e:
        logging.error(f"Database batch sync failed: {e}")
        # Fallback to individual updates
        for url, data in websites.items():
            try:
                db.update_website(url, data)
                success_count += 1
            except Exception as e:
                error_count += 1
                logging.error(f"Failed to sync {url} to database: {e}")

        logging.info(
            f"Database fallback sync: {success_count} successful, {error_count} failed")


# Historical data storage for enhanced health scoring
performance_history = {}
MAX_HISTORY_ENTRIES = 50  # Keep last 50 measurements per website


def get_historical_data(url: str) -> list:
    """Get historical performance data for a website"""
    return performance_history.get(url, [])


def add_performance_record(url: str, data: dict):
    """Add a performance record to history"""
    if url not in performance_history:
        performance_history[url] = []

    # Add current record
    performance_history[url].append({
        'timestamp': time.time(),
        'response_time': data.get('response_time'),
        'status_code': data.get('status_code'),
        'status': data.get('status'),
        'error_count': data.get('error_count', 0),
        'ssl_info': data.get('ssl_info', {})
    })

    # Keep only recent entries
    if len(performance_history[url]) > MAX_HISTORY_ENTRIES:
        performance_history[url] = performance_history[url][-MAX_HISTORY_ENTRIES:]


def calculate_health_score(url: str, current_data: dict) -> dict:
    """Calculate enhanced health score with historical context"""
    try:
        # Get historical data
        historical_data = get_historical_data(url)

        # Use enhanced health scorer
        health_data = EnhancedHealthScorer.calculate_health_score(
            current_data,
            historical_data
        )

        logging.info(
            f"Enhanced health score for {url}: {health_data['score']} "
            f"({health_data['grade']}) with {health_data.get('confidence', 0):.1f}% confidence"
        )

        return health_data

    except Exception as e:
        logging.error(
            f"Error calculating enhanced health score for {url}: {e}")
        # Fallback to basic health scoring
        return HealthScorer.calculate_health_score(current_data)


def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as file:
            return json.load(file)
    return {}


def save_metadata(metadata):
    with open(METADATA_FILE, "w") as file:
        json.dump(metadata, file, indent=4)


def update_metadata(website, screenshot_path):
    metadata = load_metadata()
    metadata[website] = {
        "last_captured": time.time(),
        "screenshot_path": screenshot_path,
    }
    save_metadata(metadata)


def get_website_ip(website_url):
    """Extract domain from URL and get its IP address"""
    try:
        # Extract domain from URL
        from urllib.parse import urlparse
        parsed = urlparse(website_url)
        domain = parsed.netloc or parsed.path.split('/')[0]

        # Remove port if present
        if ':' in domain and not domain.startswith('['):  # Handle IPv6
            domain = domain.split(':')[0]

        # Remove www. if present
        if domain.startswith('www.'):
            domain = domain[4:]

        # Try DNS resolution with timeout
        import socket
        socket.setdefaulttimeout(10)  # 10 second timeout
        ip_address = socket.gethostbyname(domain)
        logging.info(f"Resolved {domain} to {ip_address}")
        return ip_address

    except (socket.error, socket.gaierror) as e:
        logging.error(f"Failed to resolve IP for {website_url}: {e}")
        # Try alternative DNS resolution
        try:
            import dns.resolver
            result = dns.resolver.resolve(domain, 'A')
            if result:
                ip_address = str(result[0])
                logging.info(
                    f"Alternative DNS resolved {domain} to {ip_address}")
                return ip_address
        except:
            pass
        return "Unknown"
    except Exception as e:
        logging.error(f"Unexpected error resolving IP for {website_url}: {e}")
        return "Unknown"
    finally:
        socket.setdefaulttimeout(None)  # Reset timeout


def capture_screenshot(website_url, output_folder="static/screenshots", delay=3):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    metadata = load_metadata()
    options = {"headless": True, "args": ["--no-sandbox", "--disable-gpu"]}

    with sync_playwright() as p:

        try:
            screenshot_filename = (
                f"{website_url.replace('https://', '').replace('/', '_')}.png"
            )
            screenshot_path = os.path.join(output_folder, screenshot_filename)

            if not os.path.exists(screenshot_path):
                browser = p.chromium.launch(**options)
                page = browser.new_page()
                page.goto(website_url)
                page.screenshot(path=screenshot_path)
                logging.info(f"Screenshot saved for {website_url}")
                update_metadata(website_url, screenshot_path)
                browser.close()
            else:
                logging.info(f"Screenshot already exists for {website_url}")
        except Exception as e:
            logging.error(f"Error capturing screenshot for {website_url}: {e}")
        finally:
            return screenshot_filename


def add_screenshot_to_website(website):
    global websites
    try:
        last_captured = websites[website].get("last_captured")
        website_ip = websites[website].get("ip")
        if website_ip == "IP Not Found":
            return
        if (
            last_captured is None or (time.time() - last_captured) > 3600
        ):  # Check if more than an hour has passed
            screenshot_path = capture_screenshot(website)
            websites[website]["screenshot"] = screenshot_path
    except Exception as e:
        logging.error(f"Error adding screenshot for {website}: {e}")


def load_websites_from_excel(file_path: str = ""):
    global websites
    try:
        if not file_path:
            logging.warning("No file path provided for Excel loading")
            return {}

        if not os.path.exists(file_path):
            logging.warning(f"Excel file not found: {file_path}")
            return {}

        df = pd.read_excel(file_path)
        df["Domain"] = (
            df["Domain"].str.strip().str.lower()
        )  # Remove leading/trailing whitespace and convert to lowercase
        metadata = load_metadata()

        for url in df["Domain"].dropna():
            website = f"https://www.{url}/"
            ip_address = get_website_ip(url)
            website_data = {
                "ip": ip_address,
                "status": "Unknown",
                "error_count": 0,
                "status_code": 0,
                "last_captured": metadata.get(website, {}).get("last_captured"),
            }
            websites[website] = website_data

            # Add to database if not exists
            try:
                db.add_website(website, website_data)
                logging.info(f"Added {website} to database")
            except Exception as e:
                # Website might already exist, try update instead
                logging.info(
                    f"Website {website} may already exist, updating: {e}")
                db.update_website(website, website_data)

            scr_thread = Thread(
                target=add_screenshot_to_website, args=(website,))
            scr_thread.start()

        logging.info("Websites loaded from Excel")
        return websites
    except Exception as e:
        logging.error(f"Error loading Excel file: {e}")
        return {}


# Load websites from Excel only if file exists
DEFAULT_EXCEL_FILE = "websites.xlsx"
if os.path.exists(DEFAULT_EXCEL_FILE):
    load_websites_from_excel(DEFAULT_EXCEL_FILE)
else:
    logging.info(
        "No default Excel file found, starting with empty website list")


def send_email_alert(website):
    try:
        with smtplib.SMTP_SSL(EMAIL_SERVER, EMAIL_PORT) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            subject = f"Website Down Alert: {website}"
            body = f"ALERT: The website {website} is down for {
                ERROR_THRESHOLD} consecutive checks."
            message = f"Subject: {subject}\n\n{body}"
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, message)
            logging.info(f"Email alert sent for {website}")
    except Exception as e:
        logging.error(f"Failed to send email for {website}. Exception: {e}")


async def send_website_alert(url: str, alert_type: AlertType, severity: AlertSeverity,
                             title: str, message: str, details: dict = None):
    """Send alert for website issues through the alert system"""
    try:
        alert = AlertMessage(
            title=title,
            message=message,
            severity=severity,
            alert_type=alert_type,
            website_url=url,
            timestamp=datetime.now(),
            details=details
        )

        # Send alert through all configured channels
        results = await alert_manager.send_alert(alert)

        # Log results
        success_channels = [channel for channel,
                            success in results.items() if success]
        failed_channels = [channel for channel,
                           success in results.items() if not success]

        if success_channels:
            logging.info(
                f"Alert sent successfully via: {', '.join(success_channels)}")
        if failed_channels:
            logging.error(
                f"Alert failed to send via: {', '.join(failed_channels)}")

    except Exception as e:
        logging.error(f"Error sending alert for {url}: {e}")


def send_alert_sync(url: str, alert_type: AlertType, severity: AlertSeverity,
                    title: str, message: str, details: dict = None):
    """Synchronous wrapper for sending alerts"""
    try:
        # Try to get the current event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, schedule the task
            asyncio.create_task(send_website_alert(
                url, alert_type, severity, title, message, details))
        except RuntimeError:
            # No event loop running, create a new one for this alert
            def run_alert():
                asyncio.run(send_website_alert(url, alert_type,
                            severity, title, message, details))

            # Run in a separate thread to avoid blocking the monitoring
            import threading
            alert_thread = threading.Thread(target=run_alert, daemon=True)
            alert_thread.start()

    except Exception as e:
        logging.error(f"Error sending alert sync for {url}: {e}")


def check_and_send_alerts(url: str, previous_status: str = None):
    """Check for alert conditions and send alerts if needed"""
    try:
        current_status = websites[url]["status"]
        health_score = websites[url].get("health_score", {}).get("score", 0)
        ssl_info = websites[url].get("ssl_info", {})
        dns_info = websites[url].get("dns_info", {})
        response_time = websites[url].get("response_time", "0ms")

        # Convert response time to numeric for comparison
        response_time_ms = float(response_time.replace(
            "ms", "")) if "ms" in str(response_time) else 0

        # Website Down Alert
        if current_status == "DOWN" and previous_status != "DOWN":
            send_alert_sync(
                url=url,
                alert_type=AlertType.WEBSITE_DOWN,
                severity=AlertSeverity.CRITICAL,
                title=f"Website Down: {url}",
                message=f"Website {url} is currently down and not responding to requests.",
                details={
                    "status_code": websites[url].get("status_code", "N/A"),
                    "error_count": websites[url].get("error_count", 0),
                    "last_error": websites[url].get("last_error", "Unknown"),
                    "response_time": response_time
                }
            )

        # Website Up Alert (recovery)
        elif current_status == "UP" and previous_status == "DOWN":
            send_alert_sync(
                url=url,
                alert_type=AlertType.WEBSITE_UP,
                severity=AlertSeverity.LOW,
                title=f"Website Recovered: {url}",
                message=f"Website {url} is back online and responding normally.",
                details={
                    "status_code": websites[url].get("status_code", "N/A"),
                    "response_time": response_time,
                    "health_score": health_score
                }
            )

        # Slow Response Alert
        elif current_status == "UP" and response_time_ms > 5000:  # 5 seconds
            send_alert_sync(
                url=url,
                alert_type=AlertType.SLOW_RESPONSE,
                severity=AlertSeverity.MEDIUM,
                title=f"Slow Response: {url}",
                message=f"Website {url} is responding slowly ({response_time}).",
                details={
                    "response_time": response_time,
                    "threshold": "5000ms",
                    "health_score": health_score
                }
            )

        # SSL Expiring Alert
        if ssl_info and ssl_info.get("valid"):
            days_until_expiry = ssl_info.get("days_until_expiry", 999)
            if days_until_expiry <= 30 and days_until_expiry > 0:
                severity = AlertSeverity.HIGH if days_until_expiry <= 7 else AlertSeverity.MEDIUM
                send_alert_sync(
                    url=url,
                    alert_type=AlertType.SSL_EXPIRING,
                    severity=severity,
                    title=f"SSL Certificate Expiring: {url}",
                    message=f"SSL certificate for {url} expires in {days_until_expiry} days.",
                    details={
                        "days_until_expiry": days_until_expiry,
                        "expiry_date": ssl_info.get("expiry_date", "Unknown"),
                        "issuer": ssl_info.get("issuer", "Unknown")
                    }
                )

        # DNS Issues Alert
        if dns_info and dns_info.get("status") == "ERROR":
            send_alert_sync(
                url=url,
                alert_type=AlertType.DNS_ISSUE,
                severity=AlertSeverity.HIGH,
                title=f"DNS Issues: {url}",
                message=f"DNS problems detected for {url}.",
                details={
                    "dns_error": dns_info.get("error", "Unknown DNS error"),
                    "dns_health_score": dns_info.get("health_score", 0)
                }
            )

        # Low Health Score Alert
        if health_score < 50:  # Below 50% health score
            severity = AlertSeverity.HIGH if health_score < 25 else AlertSeverity.MEDIUM
            send_alert_sync(
                url=url,
                alert_type=AlertType.HEALTH_SCORE_LOW,
                severity=severity,
                title=f"Low Health Score: {url}",
                message=f"Website {url} has a low health score of {health_score:.1f}%.",
                details={
                    "health_score": health_score,
                    "health_grade": websites[url].get("health_score", {}).get("grade", "Unknown"),
                    "confidence": websites[url].get("health_score", {}).get("confidence", 0)
                }
            )

    except Exception as e:
        logging.error(f"Error checking alerts for {url}: {e}")


def check_website(url):
    global websites
    start_time = time.time()

    # Store previous status for alert comparison
    previous_status = websites[url].get("status", "Unknown")

    # Resolve IP address if not already done
    if not websites[url].get("ip") or websites[url]["ip"] == "Unknown":
        websites[url]["ip"] = get_website_ip(url)

    # Check DNS configuration
    try:
        dns_info = dns_monitor.monitor_domain(url)
        websites[url]["dns_info"] = dns_info
        logging.info(
            f"DNS check for {url}: Health score {dns_info.get('health_score', 0)} ({dns_info.get('status', 'UNKNOWN')})")
    except Exception as e:
        logging.error(f"DNS check failed for {url}: {e}")
        websites[url]["dns_info"] = {
            'status': 'ERROR',
            'error': str(e),
            'health_score': 0
        }

    # Check SSL certificate for HTTPS sites
    ssl_info = None
    if url.startswith('https://'):
        try:
            ssl_info = SSLMonitor.check_ssl_certificate(url)
            websites[url]["ssl_info"] = ssl_info
            logging.info(
                f"SSL check for {url}: Grade {ssl_info.get('grade', 'Unknown')}")
        except Exception as e:
            logging.error(f"SSL check failed for {url}: {e}")
            websites[url]["ssl_info"] = {
                'valid': False, 'error': str(e), 'grade': 'F'}

    for attempt in range(RETRY_COUNT + 1):
        try:
            response = requests.get(url, timeout=30)
            # Convert to milliseconds
            response_time = round((time.time() - start_time) * 1000, 2)

            websites[url]["status_code"] = response.status_code
            websites[url]["response_time"] = f"{response_time}ms"
            websites[url]["last_check"] = time.strftime("%Y-%m-%d %H:%M:%S")

            if response.status_code == 200:
                websites[url]["status"] = "UP"
                websites[url]["error_count"] = 0  # Reset error count
                websites[url]["last_error"] = None  # Clear any previous error

                # Calculate enhanced health score for successful check
                try:
                    current_data = {
                        'url': url,
                        'status': websites[url]["status"],
                        'status_code': websites[url].get("status_code"),
                        'response_time': websites[url].get("response_time"),
                        'error_count': websites[url].get("error_count", 0),
                        'ssl_info': websites[url].get("ssl_info", {}),
                        'dns_info': websites[url].get("dns_info", {})
                    }

                    # Add to performance history
                    add_performance_record(url, current_data)

                    # Calculate enhanced health score
                    health_data = calculate_health_score(
                        url, current_data)
                    websites[url]["health_score"] = health_data

                except Exception as e:
                    logging.error(
                        f"Error calculating enhanced health score for {url}: {e}")
                    websites[url]["health_score"] = {
                        'score': 0, 'grade': 'F', 'status': 'ERROR'}

                logging.info(
                    f"Website is available: {url} ({response_time}ms)")

                # Check for alerts after successful monitoring
                check_and_send_alerts(url, previous_status)

                return True
            else:
                error_msg = f"HTTP {response.status_code}"
                websites[url]["last_error"] = error_msg
                logging.warning(
                    f"Warning: {url} returned status code {response.status_code}")

        except requests.exceptions.ConnectTimeout as e:
            error_msg = f"Connection timeout after 30s"
            websites[url]["last_error"] = error_msg
            logging.error(f"Timeout: {url} connection timeout. Exception: {e}")
        except requests.exceptions.ReadTimeout as e:
            error_msg = f"Read timeout after 30s"
            websites[url]["last_error"] = error_msg
            logging.error(f"Timeout: {url} read timeout. Exception: {e}")
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection failed: {str(e)[:100]}"
            websites[url]["last_error"] = error_msg
            logging.error(f"Error: {url} is not reachable. Exception: {e}")
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timeout after 30s"
            websites[url]["last_error"] = error_msg
            logging.error(
                f"Timeout: {url} took too long to respond. Exception: {e}")
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)[:100]}"
            websites[url]["last_error"] = error_msg
            logging.error(f"Unexpected error checking {url}: {e}")

    # If we get here, all attempts failed
    websites[url]["error_count"] += 1
    websites[url]["last_check"] = time.strftime("%Y-%m-%d %H:%M:%S")

    if websites[url]["error_count"] >= ERROR_THRESHOLD:
        websites[url]["status"] = "DOWN"
        # send_email_alert(url)  # Uncomment if you want email alerts
    else:
        websites[url]["status"] = "SLOW"

    logging.error(f"Website {url} failed all {RETRY_COUNT + 1} attempts")

    # Calculate enhanced health score after check completes
    try:
        current_data = {
            'url': url,
            'status': websites[url]["status"],
            'status_code': websites[url].get("status_code"),
            'response_time': websites[url].get("response_time"),
            'error_count': websites[url].get("error_count", 0),
            'ssl_info': websites[url].get("ssl_info", {}),
            'dns_info': websites[url].get("dns_info", {})
        }

        # Add to performance history
        add_performance_record(url, current_data)

        # Calculate enhanced health score
        health_data = calculate_health_score(url, current_data)
        websites[url]["health_score"] = health_data

    except Exception as e:
        logging.error(
            f"Error calculating enhanced health score for {url}: {e}")
        websites[url]["health_score"] = {
            'score': 0, 'grade': 'F', 'status': 'ERROR'}

    # Check for alerts after failed monitoring
    check_and_send_alerts(url, previous_status)

    logging.error(
        f"{url} has been down for {websites[url]['error_count']} consecutive checks")
    return False


def check_websites():
    """Check all websites in the global websites dictionary"""
    if not websites:
        logging.info("No websites to check")
        return

    logging.info(f"Starting check for {len(websites)} websites")

    threads = []
    # Create a copy of keys to avoid modification during iteration
    for website in list(websites.keys()):
        web_thread = Thread(target=check_website, args=(website,))
        web_thread.start()
        threads.append(web_thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Batch sync all website data to database after monitoring cycle
    logging.info("Syncing website data to database...")
    try:
        sync_websites_to_db()
        logging.info("Database sync completed successfully")
    except Exception as e:
        logging.error(f"Database sync failed: {e}")

    logging.info("Completed checking all websites")


def periodic_monitoring(interval=3600):  # 1 hour by default
    while True:
        check_websites()
        time.sleep(interval)
