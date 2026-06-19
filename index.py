# ============================================
# 🚗 PREMIUM VEHICLE & CHALLAN INFO API (White-Labeled)
# 👑 Dev: @sakib01994 • 💳 Src: Custom Premium Gateway
# ============================================

from flask import Flask, request, jsonify
import requests
import re
from bs4 import BeautifulSoup

app = Flask(__name__)

# ==================== CONFIGURATION ====================
DEBUG_MODE = False
REQUEST_TIMEOUT = 25  # Vercel Limit (30s)
DEVELOPER = "@sakib01994"
CREDIT = "SB-SAKIB @sakib01994"
BASE_URL = "https://vahanx.in"

# Memory Cache
volatile_cache = {}

# ==================== CLEANING & FILTERING UTILITIES ====================

def sanitize_text(text):
    """
    Removes any trace of the source website, branding, or support emails.
    """
    if not text:
        return ""
    
    # Remove specific source traces (Case-Insensitive)
    text = re.sub(r'vahanx\.in', '', text, flags=re.IGNORECASE)
    text = re.sub(r'vahanx', '', text, flags=re.IGNORECASE)
    text = re.sub(r'support@\S*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'https?://\S*', '', text, flags=re.IGNORECASE)
    
    # Clean extra spaces, dashes or colons left behind
    text = re.sub(r'[:||\-\s]+$', '', text).strip()
    text = re.sub(r'^[:||\-\s]+', '', text).strip()
    
    return text

def is_junk_field(key, val):
    """
    Filters out rows that only contain copyright, links, or contact info of the source site.
    """
    junk_keywords = ['vahanx', 'support@', 'telegram', 'channel', 'website', 'developer', 'copyright', 'contact us']
    combined = f"{key} {val}".lower()
    return any(kw in combined for kw in junk_keywords)

# ==================== ADVANCED PARSER ====================

def extract_all_details(html_content):
    """
    Scrapes EVERY single available key-value data point, tables, 
    and fields from the HTML while removing source branding.
    """
    extracted_data = {}
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. Capture data from ALL HTML Tables
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    raw_key = cols[0].get_text(" ", strip=True)
                    raw_val = cols[1].get_text(" ", strip=True)
                    
                    key = sanitize_text(raw_key)
                    val = sanitize_text(raw_val)
                    
                    if key and val and not is_junk_field(raw_key, raw_val):
                        extracted_data[key] = val

        # 2. Capture data from List Groups, Cards, or Div-based Key-Value Pairs
        # This ensures mobile numbers or hidden fields inside divs are not missed
        for element in soup.find_all(['div', 'li', 'p']):
            # If element has no children and has text containing potential data separators
            if not element.find() and (':' in element.get_text() or '—' in element.get_text()):
                text = element.get_text(strip=True)
                parts = re.split(r'[:—]', text, maxsplit=1)
                if len(parts) == 2:
                    raw_key = parts[0].strip()
                    raw_val = parts[1].strip()
                    
                    key = sanitize_text(raw_key)
                    val = sanitize_text(raw_val)
                    
                    if key and val and not is_junk_field(raw_key, raw_val):
                        extracted_data[key] = val

        # 3. Dedicated Regex Fallback for Mobile Numbers (just in case it's embedded in raw text or inputs)
        # Looks for standard 10-digit Indian mobile numbers prefixed with values like value="98765..."
        mobile_matches = re.findall(r'value="([6-9]\d{9})"', html_content)
        if mobile_matches:
            extracted_data["Mobile Number"] = mobile_matches[0]
            
        # Generic text pattern for mobile numbers in HTML body
        text_mobiles = re.findall(r'(?:Mobile|Phone|Contact|💥)\s*(?:No|Number)?\s*[:—]?\s*([6-9]\d{9})', soup.get_text(), re.IGNORECASE)
        if text_mobiles and "Mobile Number" not in extracted_data:
            extracted_data["Mobile Number"] = text_mobiles[0]

    except Exception as e:
        pass
    
    return extracted_data

# ==================== CORE FETCH LOGIC ====================

def get_premium_headers():
    return {
        'Host': 'vahanx.in',
        'Connection': 'keep-alive',
        'sec-ch-ua': '"Chromium";v="148", "Android WebView";v="148", "Not/A)Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 15; V2310 Build/AP3A.240905.015.A2_NNCS) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.7778.215 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'X-Requested-With': 'mark.via.gp',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Referer': 'https://vahanx.in/',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8'
    }

def fetch_data_from_source(endpoint, vehicle_number, session_cookies):
    try:
        url = f"{BASE_URL}/{endpoint}/{vehicle_number}"
        response = requests.get(
            url, 
            headers=get_premium_headers(), 
            cookies=session_cookies, 
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            return extract_all_details(response.text)
    except:
        pass
    return {}

# ==================== ROUTES ====================

@app.route("/")
def index():
    return jsonify({
        "status": "online",
        "message": "Premium White-Labeled Vehicle Gateway",
        "usage": "/fetch?vehicle=GJ21DB1119",
        "owner": DEVELOPER
    })

@app.route("/fetch", methods=["GET"])
def fetch():
    vehicle = request.args.get("vehicle", "").strip().upper()
    vehicle = re.sub(r'[^A-Z0-9]', '', vehicle)

    if not vehicle or len(vehicle) < 6:
        return jsonify({"status": "error", "message": "Invalid Vehicle Number"}), 400

    # Cache Check
    if vehicle in volatile_cache:
        return jsonify(volatile_cache[vehicle])

    # Cookie Parsing
    custom_cookie_str = request.headers.get("X-Vahan-Cookie") or request.args.get("cookies", "")
    cookies = {}
    if custom_cookie_str:
        try:
            cookies = dict(item.split("=") for item in custom_cookie_str.split("; "))
        except:
            pass

    # Concurrent-style sequential fetching for all data points
    rc_details = fetch_data_from_source("rc-search", vehicle, cookies)
    challan_details = fetch_data_from_source("challan-search", vehicle, cookies)

    # If both failed or returned empty
    if not rc_details and not challan_details:
        return jsonify({
            "status": "error",
            "message": "No data found or session cookies expired."
        }), 404

    # Master Clean JSON Response Structure
    response_data = {
        "status": "success",
        "developer": DEVELOPER,
        "credit": CREDIT,
        "vehicle_number": vehicle,
        "registration_details": rc_details if rc_details else "No Record Found",
        "challan_details": challan_details if challan_details else "No Record Found"
    }

    # Save to dynamic cache
    volatile_cache[vehicle] = response_data
    
    return jsonify(response_data)

# Vercel Deployment Settings
app.debug = DEBUG_MODE
