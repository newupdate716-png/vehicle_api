# ============================================
# 🚗 PREMIUM VEHICLE & CHALLAN INFO API (Vercel Optimized)
# 👑 Dev: @sakib01994 • 💳 Src: VahanX Premium
# ============================================

from flask import Flask, request, jsonify
import requests
import re
from bs4 import BeautifulSoup

app = Flask(__name__)

# ==================== CONFIGURATION ====================
DEBUG_MODE = False
REQUEST_TIMEOUT = 25  # Vercel Hobby Tier Limit (30s)
DEVELOPER = "@sakib01994"
CREDIT = "SB-SAKIB @sakib01994"
BASE_URL = "https://vahanx.in"

# Memory Cache (Temporary storage on Vercel instances)
volatile_cache = {}

# ==================== HELPER FUNCTIONS ====================

def get_premium_headers():
    """
    Returns standard headers extracted from your working cURL requests
    """
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

def parse_vahan_html(html_content):
    """
    Extracts key-value pair data from response tables dynamically
    """
    extracted_data = {}
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for data tables inside the responsive structure
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    key = cols[0].get_text(strip=True).replace(':', '').strip()
                    val = cols[1].get_text(strip=True).strip()
                    if key:
                        extracted_data[key] = val

        # Fallback to look for list groups or simple key-value displays if tables are absent
        if not extracted_data:
            div_items = soup.find_all('div', class_=re.compile(r'(detail|info|row)'))
            for item in div_items:
                text = item.get_text(separator="||", strip=True)
                parts = text.split("||")
                if len(parts) >= 2:
                    key = parts[0].replace(':', '').strip()
                    val = parts[1].strip()
                    extracted_data[key] = val

    except Exception as e:
        pass
    
    return extracted_data

def fetch_rc_details(vehicle_number, session_cookies=None):
    """
    Fetches Registration Certificate (RC) Information
    """
    try:
        url = f"{BASE_URL}/rc-search/{vehicle_number}"
        response = requests.get(
            url, 
            headers=get_premium_headers(), 
            cookies=session_cookies, 
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            parsed_data = parse_vahan_html(response.text)
            if parsed_data:
                return {"success": True, "data": parsed_data}
            return {"success": True, "raw_html_snippet": response.text[:1000]} # Fallback if structure changes
            
        return {"success": False, "error": f"RC Endpoint returned status {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def fetch_challan_details(vehicle_number, session_cookies=None):
    """
    Fetches Challan/Fine Information
    """
    try:
        url = f"{BASE_URL}/challan-search/{vehicle_number}"
        response = requests.get(
            url, 
            headers=get_premium_headers(), 
            cookies=session_cookies, 
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            parsed_data = parse_vahan_html(response.text)
            if parsed_data:
                return {"success": True, "data": parsed_data}
            return {"success": True, "raw_html_snippet": response.text[:1000]}
            
        return {"success": False, "error": f"Challan Endpoint returned status {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== ROUTES ====================

@app.route("/")
def index():
    return jsonify({
        "status": "online",
        "message": "Premium Vehicle & Challan Multi-Source API",
        "usage": "/fetch?vehicle=GJ21DB1119",
        "owner": DEVELOPER
    })

@app.route("/fetch", methods=["GET"])
def fetch():
    vehicle = request.args.get("vehicle", "").strip().upper()
    vehicle = re.sub(r'[^A-Z0-9]', '', vehicle)

    if not vehicle or len(vehicle) < 6:
        return jsonify({"status": "error", "message": "Invalid Vehicle Number"}), 400

    # Check Memory Cache
    if vehicle in volatile_cache:
        return jsonify(volatile_cache[vehicle])

    # Dynamic Cookie Management (Optional but highly recommended)
    # Pass 'cookie_str' in headers or query parameters if the session tokens expire.
    custom_cookie_str = request.headers.get("X-Vahan-Cookie") or request.args.get("cookies", "")
    cookies = {}
    
    if custom_cookie_str:
        try:
            cookies = dict(item.split("=") for item in custom_cookie_str.split("; "))
        except:
            pass

    # 1. Fetch RC Details
    rc_result = fetch_rc_details(vehicle, session_cookies=cookies)
    
    # 2. Fetch Challan Details
    challan_result = fetch_challan_details(vehicle, session_cookies=cookies)

    # Validate Responses
    if not rc_result["success"] and not challan_result["success"]:
        return jsonify({
            "status": "error",
            "message": "Failed to extract data from target endpoints. Verify session cookies.",
            "rc_error": rc_result.get("error"),
            "challan_error": challan_result.get("error")
        }), 500

    # Merge Data for Premium Clean Output
    response_data = {
        "status": "success",
        "developer": DEVELOPER,
        "credit": CREDIT,
        "vehicle_number": vehicle,
        "rc_data": rc_result.get("data", rc_result.get("raw_html_snippet", "Not Found")),
        "challan_data": challan_result.get("data", challan_result.get("raw_html_snippet", "Not Found"))
    }

    # Store inside temporary cache
    volatile_cache[vehicle] = response_data
    
    return jsonify(response_data)

# Required for Vercel Serverless Function Execution
app.debug = DEBUG_MODE
