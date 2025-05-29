import subprocess
import time
import requests
import mysql.connector
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
import signal
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(filename='main_script.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s')

# ==== CONFIGURATION ====
check_url = "https://ipinfo.io/json"
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '82.180.144.17'),
    'user': os.getenv('DB_USER', 'ip'),
    'password': os.getenv('DB_PASSWORD', 'admin@1234#'),
    'database': os.getenv('DB_NAME', 'IP_satish_sir')
}
LOOP_FOREVER = True

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
]

EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'email': 'clickrate4@gmail.com',
    'password': 'ztkg lwhk kbcs puov',
    'to_email': [
        'gautamsharma@phx.co.in',
        'satish@phoenixsoftwares.in',
        ''
    ]
}

# Global database connection for signal handler
db_connection = None
db_cursor = None

# ==== SIGNAL HANDLER ====
def signal_handler(sig, frame):
    logging.info("Received SIGTERM, shutting down gracefully...")
    if db_cursor:
        db_cursor.close()
    if db_connection:
        db_connection.close()
    logging.info("Database connections closed. Exiting.")
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)

# ==== UTILITY FUNCTIONS ====
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")
    logging.info(msg)

def get_db_connection():
    global db_connection
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        return db_connection
    except Exception as e:
        log(f"❌ Error connecting to database: {e}")
        raise

def get_active_devices():
    global db_cursor
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT adb_id FROM device WHERE is_selected = 1")
            rows = cursor.fetchall()
            devices = [row[0] for row in rows if row[0]]
            log(f"Found {len(devices)} selected devices: {devices}")
            return devices
    except Exception as e:
        log(f"❌ Error fetching devices: {e}")
        return []

def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['email']
        msg['To'] = ", ".join([email for email in EMAIL_CONFIG['to_email'] if email])
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.ehlo()
        server.starttls()
        server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        server.send_message(msg, from_addr=EMAIL_CONFIG['email'], to_addrs=[email for email in EMAIL_CONFIG['to_email'] if email])
        server.quit()

        log(f"📧 Email sent: {subject}")
    except Exception as e:
        log(f"❌ Failed to send email: {e}")

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def create_tables_if_not_exists():
    global db_cursor
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ip_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    device VARCHAR(255),
                    ip VARCHAR(45),
                    city VARCHAR(255),
                    region VARCHAR(255),
                    country VARCHAR(10),
                    location VARCHAR(255),
                    org VARCHAR(255),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS url_clicks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    url TEXT,
                    target_clicks INT,
                    unique_percent INT,
                    repeated_percent INT,
                    unique_clicks_done INT DEFAULT 0,
                    repeated_clicks_done INT DEFAULT 0,
                    total_delivery INT DEFAULT 0,
                    last_email_sent VARCHAR(10) DEFAULT NULL,
                    is_selected BOOLEAN DEFAULT 0
                )
            """)
            conn.commit()
            log("Database tables checked/created successfully")
    except Exception as e:
        log(f"❌ Error creating tables: {e}")

def insert_ip_info(ip_info, device):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ip_logs (device, ip, city, region, country, location, org)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                device,
                ip_info.get("ip", ""),
                ip_info.get("city", ""),
                ip_info.get("region", ""),
                ip_info.get("country", ""),
                ip_info.get("loc", ""),
                ip_info.get("org", "")
            ))
            conn.commit()
            log(f"Inserted IP info for device {device}")
    except Exception as e:
        log(f"❌ Error inserting IP info: {e}")

def ip_exists_recent(ip):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM ip_logs
                WHERE ip = %s AND timestamp >= NOW() - INTERVAL 3 DAY
            """, (ip,))
            result = cursor.fetchone()
            return result[0] > 0
    except Exception as e:
        log(f"❌ Error checking IP existence: {e}")
        return False

def cleanup_old_ips():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ip_logs WHERE timestamp < NOW() - INTERVAL 3 DAY")
            conn.commit()
            log("Cleaned up old IPs")
    except Exception as e:
        log(f"❌ Error cleaning old IPs: {e}")

def get_url_click_data():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM url_clicks WHERE is_selected = 1")
            urls = cursor.fetchall()
            log(f"Found {len(urls)} selected URLs")
            return urls
    except Exception as e:
        log(f"❌ Error fetching URL click data: {e}")
        return []

def update_url_click_counts(url, unique_done, repeated_done):
    total_done = unique_done + repeated_done
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE url_clicks
                SET unique_clicks_done = %s,
                    repeated_clicks_done = %s,
                    total_delivery = %s
                WHERE url = %s
            """, (unique_done, repeated_done, total_done, url))
            conn.commit()
            log(f"Updated click counts for {url}: unique={unique_done}, repeated={repeated_done}, total={total_done}")
    except Exception as e:
        log(f"❌ Error updating click counts: {e}")

def update_email_status(url, status):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE url_clicks
                SET last_email_sent = %s
                WHERE url = %s
            """, (status, url))
            conn.commit()
            log(f"Updated email status for {url}: {status}")
    except Exception as e:
        log(f"❌ Error updating email status: {e}")

def get_random_old_ip():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ip FROM ip_logs ORDER BY RAND() LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        log(f"❌ Error fetching old IP: {e}")
        return None

def run_adb(device, cmd):
    try:
        out = subprocess.run(f"adb -s {device} {cmd}", shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        log(f"ADB command executed on {device}: {cmd}")
        return out.stdout.decode().strip()
    except subprocess.CalledProcessError as e:
        log(f"❌ ADB error on {device}: {e.stderr.decode().strip()}")
        return None

def get_public_ip():
    try:
        r = requests.get(check_url, timeout=10)
        ip_info = r.json()
        log(f"Fetched public IP: {ip_info.get('ip')}")
        return ip_info
    except Exception as e:
        log(f"⚠️ Requests failed: {e}")
        return None

def human_sleep(min_sec=0, max_sec=1):
    t = random.uniform(min_sec, max_sec)
    log(f"⏳ Sleeping for {t:.2f} seconds")
    time.sleep(t)

def click_url_selenium(url, user_agent):
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            url = 'http://' + url

        options = Options()
        options.add_argument(f"user-agent={user_agent}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--headless")

        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(20)
        driver.get(url)
        driver.quit()

        log(f"✅ Selenium click successful for {url}")
        return True
    except Exception as e:
        log(f"❌ Selenium click error for {url}: {e}")
        return False

def enable_usb_tethering(device):
    run_adb(device, "shell svc usb setFunctions rndis")
    time.sleep(1.5)
    log(f"Enabled USB tethering for {device}")

def disable_usb_tethering(device):
    run_adb(device, "shell svc usb setFunctions none")
    time.sleep(1.0)
    log(f"Disabled USB tethering for {device}")

def rotate_ip(device):
    run_adb(device, "shell cmd connectivity airplane-mode enable")
    time.sleep(1)
    run_adb(device, "shell cmd connectivity airplane-mode disable")
    time.sleep(1)
    run_adb(device, "shell svc data enable")
    time.sleep(2)
    log(f"Rotated IP for {device}")

def check_and_send_delivery_email(url, total_done, target, last_email_sent):
    percent_done = (total_done / target) * 100
    if percent_done >= 100 and last_email_sent != '100':
        send_email("🎯 100% Click Delivery Complete", f"All clicks delivered for URL:\n\n{url}")
        update_email_status(url, '100')
        log(f"✅ 100% delivery done for {url}")
        return '100'
    elif percent_done >= 80 and last_email_sent not in ['80', '100']:
        send_email("⚠️ 80% Click Delivery Reached", f"80% of target clicks delivered for URL:\n\n{url}")
        update_email_status(url, '80')
        return '80'
    return last_email_sent

def process_device(device):
    log(f"🔄 Starting process for {device}...")
    url_click_data = get_url_click_data()
    if not url_click_data:
        log("ℹ️ No selected URLs to process")
        return

    for data in url_click_data:
        url = data['url']
        target_clicks = data['target_clicks']
        unique_percent = data['unique_percent']
        repeated_percent = data['repeated_percent']
        unique_done = data['unique_clicks_done']
        repeated_done = data['repeated_clicks_done']
        last_email_sent = data.get('last_email_sent')
        total_done = unique_done + repeated_done

        last_email_sent = check_and_send_delivery_email(url, total_done, target_clicks, last_email_sent)

        if total_done >= target_clicks:
            log(f"Skipping {url}: Target clicks reached")
            continue

        unique_target = int(target_clicks * unique_percent / 100)
        repeated_target = int(target_clicks * repeated_percent / 100)

        while total_done < target_clicks:
            do_unique = unique_done < unique_target and (repeated_done >= repeated_target or random.randint(1, 2) == 1)

            if do_unique:
                rotate_ip(device)
                enable_usb_tethering(device)
                ip_info = get_public_ip()
                if not ip_info:
                    disable_usb_tethering(device)
                    human_sleep(1, 2)
                    continue
                public_ip = ip_info.get('ip')
                if ip_exists_recent(public_ip):
                    disable_usb_tethering(device)
                    log(f"IP {public_ip} recently used, skipping")
                    human_sleep(2, 5)
                    continue
                insert_ip_info(ip_info, device)
                user_agent = get_random_user_agent()
                success = click_url_selenium(url, user_agent)
                if success:
                    unique_done += 1
                    update_url_click_counts(url, unique_done, repeated_done)
                disable_usb_tethering(device)
            else:
                if repeated_done >= repeated_target:
                    log(f"Repeated target reached for {url}")
                    continue
                old_ip = get_random_old_ip()
                if not old_ip:
                    log("No old IPs available for repeated click")
                    continue
                user_agent = get_random_user_agent()
                success = click_url_selenium(url, user_agent)
                if success:
                    repeated_done += 1
                    update_url_click_counts(url, unique_done, repeated_done)

            total_done = unique_done + repeated_done
            last_email_sent = check_and_send_delivery_email(url, total_done, target_clicks, last_email_sent)
            human_sleep(1, 2)

def main():
    create_tables_if_not_exists()
    cleanup_old_ips()
    while True:
        devices = get_active_devices()
        if not devices:
            log("ℹ️ No selected devices found, waiting...")
            time.sleep(1)
            continue
        for device in devices:
            process_device(device)
        if not LOOP_FOREVER:
            break
        time.sleep(1)  # Avoid excessive CPU usage

if __name__ == "__main__":
    main()