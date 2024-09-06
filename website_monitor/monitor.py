import smtplib
import socket
import pandas as pd
import requests
import logging
import threading
import os
import time

# Load environment variables
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

# Configure logging
logging.basicConfig(filename='website_monitor.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def get_website_ip(website_url):
    try:
        return socket.gethostbyname(website_url)
    except socket.error:
        return 'IP Not Found'

# Read websites from the Excel file
def load_websites_from_excel(file_path):
    try:
        df = pd.read_excel(file_path)
        df['Domain'] = df['Domain'].str.strip()  # Remove leading/trailing whitespace
        df['Domain'] = df['Domain'].str.lower()  # Convert to lowercase
        data = {}

        for url in df['Domain'].dropna():
            ip_address = get_website_ip(url.strip())
            data[f"https://www.{url.strip()}/"] = {"ip": ip_address, "status": "Unknown", "error_count": 0, "status_code": 0}
        return data
    except Exception as e:
        logging.error(f"Error loading Excel file: {e}")
        return {}

# Load websites from Excel
websites = load_websites_from_excel('website_monitor\\domainler.xlsx')

# Constants
ERROR_THRESHOLD = 3  # Alert if down for 3 consecutive checks
RETRY_COUNT = 2

def send_email_alert(website):
    try:
        with smtplib.SMTP_SSL("mail.karehalilar.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            subject = f"Website Down Alert: {website}"
            body = f"ALERT: The website {website} is down for {ERROR_THRESHOLD} consecutive checks."
            message = f"Subject: {subject}\n\n{body}"
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, message)
            logging.info(f"Email alert sent for {website}")
    except Exception as e:
        logging.error(f"Failed to send email for {website}. Exception: {e}")


    
            
def check_website(url):
    global websites
    for _ in range(RETRY_COUNT + 1):
        try:
            response = requests.get(url, timeout=10)
            websites[url]["status_code"] = response.status_code 
            if response.status_code == 200:
                websites[url]["status"] = "Up"                
                websites[url]["error_count"] = 0  # Reset error count
                logging.info(f"Website is available: {url}")
                return True
            else:
                logging.warning(f"Error: {url} returned status code {response.status_code}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error: {url} is not reachable. Exception: {e}")

    websites[url]["error_count"] += 1  # Increment error count
    if websites[url]["error_count"] >= ERROR_THRESHOLD:
        websites[url]["status"] = "Down"
    else:
        websites[url]["status"] = "Error"

    # Send email alert if down
    send_email_alert(url)
    
    logging.error(f"{url} has been down for {websites[url]['error_count']} consecutive checks")
    return False

def check_websites():
    threads = []
    for website in websites:
        thread = threading.Thread(target=check_website, args=(website,))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()

# Continuous background check (for the Flask app)
def start_monitoring():
    while True:
        check_websites()
        time.sleep(1800)  # Check every 5 minutes
