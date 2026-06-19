# ============================================
# 🚗 PREMIUM VEHICLE & CHALLAN INFO API (White-Labeled)
# 👑 Dev: @sakib01994 • 💳 Src: Custom Premium Gateway
# ============================================

from flask import Flask, request, jsonify
import requests
import re
import json
import hashlib
import time
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

app = Flask(__name__)

# ==================== CONFIGURATION ====================
DEBUG_MODE = False
REQUEST_TIMEOUT = 25
DEVELOPER = "@sakib01994"
CREDIT = "SB-SAKIB @sakib01994"
BASE_URL = "https://vahanx.in"
CACHE_DURATION = 300  # 5 minutes cache

# Enhanced Memory Cache with TTL
cache = {}
cache_timestamps = {}

# ==================== CACHE MANAGEMENT ====================

def get_from_cache(key):
    """Get cached data with TTL check"""
    if key in cache and key in cache_timestamps:
        if time.time() - cache_timestamps[key] < CACHE_DURATION:
            return cache[key]
        else:
            # Clear expired cache
            del cache[key]
            del cache_timestamps[key]
    return None

def set_to_cache(key, data):
    """Store data in cache with timestamp"""
    cache[key] = data
    cache_timestamps[key] = time.time()

# ==================== CLEANING & FILTERING UTILITIES ====================

def sanitize_text(text):
    """Remove source website traces and clean text"""
    if not text:
        return ""
    
    # Remove specific source traces
    text = re.sub(r'vahanx\.in', '', text, flags=re.IGNORECASE)
    text = re.sub(r'vahanx', '', text, flags=re.IGNORECASE)
    text = re.sub(r'support@\S*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'https?://\S*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'telegram\.me\S*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'@\S+', '', text, flags=re.IGNORECASE)
    
    # Clean extra spaces, dashes, colons
    text = re.sub(r'[:||\-–—\s]+$', '', text).strip()
    text = re.sub(r'^[:||\-–—\s]+', '', text).strip()
    
    return text.strip()

def is_junk_field(key, val):
    """Filter out junk/branding fields"""
    junk_keywords = ['vahanx', 'support@', 'telegram', 'channel', 'website', 
                     'developer', 'copyright', 'contact us', 'copyright', 
                     'all rights', 'reserved', 'powered by', 'visit us']
    combined = f"{key} {val}".lower()
    return any(kw in combined for kw in junk_keywords)

def format_indian_currency(text):
    """Format Indian currency values"""
    if not text:
        return text
    # Remove any non-numeric characters except decimal
    cleaned = re.sub(r'[^\d.]', '', text)
    if cleaned:
        try:
            value = float(cleaned)
            return f"₹{value:,.2f}"
        except:
            pass
    return text

# ==================== ADVANCED PARSER ====================

def extract_all_details(html_content, is_challan=False):
    """
    Advanced scraping of ALL data points from HTML
    """
    extracted_data = {}
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # 1. Extract from ALL Tables
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    raw_key = cols[0].get_text(" ", strip=True)
                    raw_val = cols[1].get_text(" ", strip=True)
                    
                    # Clean but preserve important data
                    key = sanitize_text(raw_key)
                    val = sanitize_text(raw_val)
                    
                    if key and val and not is_junk_field(raw_key, raw_val):
                        # Format currency if applicable
                        if any(word in key.lower() for word in ['amount', 'fine', 'penalty', 'fee', 'tax']):
                            val = format_indian_currency(val)
                        extracted_data[key] = val

        # 2. Extract from Div-based Key-Value pairs
        for element in soup.find_all(['div', 'li', 'p', 'span']):
            # Check for structured data
            text = element.get_text(strip=True)
            
            # Look for key-value patterns
            patterns = [
                r'([^:—–\n]+)[:—–]\s*([^:—–\n]+)',
                r'([^:—–\n]+)\s+[—–]\s+([^:—–\n]+)',
                r'([^:—–\n]+)\s*:\s*([^:—–\n]+)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    if len(match) == 2:
                        raw_key = match[0].strip()
                        raw_val = match[1].strip()
                        
                        key = sanitize_text(raw_key)
                        val = sanitize_text(raw_val)
                        
                        if key and val and not is_junk_field(raw_key, raw_val):
                            # Clean up email-like values
                            if '@' in val and 'support' in val.lower():
                                continue
                            extracted_data[key] = val

        # 3. Extract from Input fields (hidden values)
        for input_tag in soup.find_all('input'):
            if input_tag.get('type') == 'hidden' or input_tag.get('type') == 'text':
                name = input_tag.get('name', '')
                value = input_tag.get('value', '')
                if name and value and len(value) >= 4:
                    # Check if it's a mobile number or important data
                    if re.match(r'[6-9]\d{9}', value):
                        extracted_data["Mobile Number"] = value
                    elif name.lower() not in ['_token', '_method', 'csrf']:
                        key = sanitize_text(name.replace('_', ' ').title())
                        val = sanitize_text(value)
                        if key and val and not is_junk_field(key, val):
                            extracted_data[key] = val

        # 4. Special extraction for mobile numbers
        # Pattern for Indian mobile numbers
        mobile_patterns = [
            r'(?:Mobile|Phone|Contact|WhatsApp|📱|📞)\s*(?:No|Number)?\s*[:—–]?\s*([6-9]\d{9})',
            r'value="([6-9]\d{9})"',
            r'>([6-9]\d{9})<',
            r'\b([6-9]\d{9})\b'
        ]
        
        for pattern in mobile_patterns:
            matches = re.findall(pattern, html_content)
            if matches and "Mobile Number" not in extracted_data:
                extracted_data["Mobile Number"] = matches[0]
                break

        # 5. Extract Vehicle Registration details specifically
        reg_patterns = {
            'Registration Date': r'(?:Reg(?:istration)?\s*Date|Date of Registration)\s*[:—–]?\s*(\d{2}[-/]\d{2}[-/]\d{4})',
            'Registration Number': r'(?:Reg(?:istration)?\s*(?:No|Number)?)\s*[:—–]?\s*([A-Z0-9]{6,})',
            'Chassis Number': r'(?:Chassis\s*(?:No|Number)?)\s*[:—–]?\s*([A-Z0-9]{10,})',
            'Engine Number': r'(?:Engine\s*(?:No|Number)?)\s*[:—–]?\s*([A-Z0-9]{6,})',
            'Owner Name': r'(?:Owner\s*(?:Name)?)\s*[:—–]?\s*([A-Za-z\s\.]+)',
            'Vehicle Class': r'(?:Vehicle\s*Class|Class)\s*[:—–]?\s*([A-Za-z\s]+)',
            'Fuel Type': r'(?:Fuel\s*Type)\s*[:—–]?\s*([A-Za-z\s]+)',
            'Colour': r'(?:Colour|Color)\s*[:—–]?\s*([A-Za-z\s]+)',
            'Manufacturer': r'(?:Manufacturer|Maker)\s*[:—–]?\s*([A-Za-z\s\.]+)',
            'Model': r'(?:Model)\s*[:—–]?\s*([A-Za-z0-9\s\-]+)'
        }
        
        for key, pattern in reg_patterns.items():
            if key not in extracted_data:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    extracted_data[key] = match.group(1).strip()

        # 6. Challan specific extraction
        if is_challan:
            challan_patterns = {
                'Challan Number': r'(?:Challan\s*(?:No|Number)?)\s*[:—–]?\s*([A-Z0-9\-]+)',
                'Fine Amount': r'(?:Fine|Penalty|Amount)\s*[:—–]?\s*(?:₹|Rs\.?)?\s*([\d,]+\.?\d*)',
                'Status': r'(?:Status|Payment Status)\s*[:—–]?\s*([A-Za-z\s]+)',
                'Date': r'(?:Date|Challan Date)\s*[:—–]?\s*(\d{2}[-/]\d{2}[-/]\d{4})',
                'Location': r'(?:Location|Place)\s*[:—–]?\s*([A-Za-z\s,]+)',
                'Offence': r'(?:Offence|Violation)\s*[:—–]?\s*([A-Za-z\s,]+)'
            }
            
            for key, pattern in challan_patterns.items():
                if key not in extracted_data:
                    match = re.search(pattern, html_content, re.IGNORECASE)
                    if match:
                        val = match.group(1).strip()
                        if 'amount' in key.lower():
                            val = format_indian_currency(val)
                        extracted_data[key] = val

        # 7. Additional data from meta tags
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name', '').lower()
            content = meta.get('content', '')
            if name and content and name not in ['viewport', 'robots', 'csrf-token']:
                if any(keyword in name for keyword in ['author', 'title', 'description']):
                    key = name.title().replace('_', ' ')
                    val = sanitize_text(content)
                    if val and not is_junk_field(key, val):
                        extracted_data[key] = val

        # 8. Extract from card-like structures
        for card in soup.find_all(['div', 'section'], class_=re.compile(r'card|box|info|detail', re.I)):
            card_text = card.get_text(" ", strip=True)
            # Look for labeled data in cards
            lines = card_text.split('\n')
            for line in lines:
                if ':' in line or '—' in line:
                    parts = re.split(r'[:—–]', line, maxsplit=1)
                    if len(parts) == 2:
                        raw_key = parts[0].strip()
                        raw_val = parts[1].strip()
                        
                        key = sanitize_text(raw_key)
                        val = sanitize_text(raw_val)
                        
                        if key and val and len(key) > 2 and len(val) > 1:
                            if not is_junk_field(raw_key, raw_val):
                                if 'amount' in key.lower() or 'fine' in key.lower():
                                    val = format_indian_currency(val)
                                extracted_data[key] = val

    except Exception as e:
        # Log error but continue
        pass
    
    return extracted_data

# ==================== HEADERS & SESSION MANAGEMENT ====================

def get_premium_headers():
    """Get premium headers for request"""
    return {
        'Host': 'vahanx.in',
        'Connection': 'keep-alive',
        'sec-ch-ua': '"Chromium";v="148", "Android WebView";v="148", "Not/A)Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 15; V2310 Build/AP3A.240905.015.A2_NNCS) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.7778.215 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'dnt': '1',
        'X-Requested-With': 'mark.via.gp',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Referer': 'https://vahanx.in/',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8'
    }

def create_session_from_cookie(cookie_string):
    """Create session from cookie string"""
    session = requests.Session()
    if cookie_string:
        try:
            # Parse cookie string
            cookies = {}
            for item in cookie_string.split('; '):
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookies[key] = value
            session.cookies.update(cookies)
        except:
            pass
    return session

# ==================== CORE FETCH LOGIC ====================

def fetch_from_source(endpoint, vehicle_number, session_cookies=None):
    """
    Fetch data from source with retry logic
    """
    max_retries = 2
    for attempt in range(max_retries):
        try:
            url = f"{BASE_URL}/{endpoint}/{vehicle_number}"
            
            # Create session with cookies
            session = requests.Session()
            if session_cookies:
                try:
                    for cookie in session_cookies.split('; '):
                        if '=' in cookie:
                            key, value = cookie.split('=', 1)
                            session.cookies.set(key, value)
                except:
                    pass
            
            # Add headers
            session.headers.update(get_premium_headers())
            
            # Make request
            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                # Check if we got valid data
                if len(response.text) > 1000:  # Minimum content length
                    return response.text
                else:
                    # Try with default session if cookie failed
                    if attempt == 0 and session_cookies:
                        continue
                    return response.text
            elif response.status_code == 429:  # Rate limit
                time.sleep(2)
                continue
                
        except Exception as e:
            if attempt == max_retries - 1:
                return None
            time.sleep(1)
            continue
    
    return None

def process_vehicle_data(vehicle_number, cookies=None):
    """
    Process vehicle data with advanced extraction
    """
    # Check cache first
    cache_key = hashlib.md5(f"{vehicle_number}_{cookies}".encode()).hexdigest()
    cached = get_from_cache(cache_key)
    if cached:
        return cached
    
    # Fetch RC details
    rc_html = fetch_from_source("rc-search", vehicle_number, cookies)
    rc_data = {}
    if rc_html:
        rc_data = extract_all_details(rc_html, is_challan=False)
    
    # Fetch Challan details
    challan_html = fetch_from_source("challan-search", vehicle_number, cookies)
    challan_data = {}
    if challan_html:
        challan_data = extract_all_details(challan_html, is_challan=True)
    
    # Handle no data case
    if not rc_data and not challan_data:
        result = {
            "status": "error",
            "message": "No data found for this vehicle number",
            "vehicle_number": vehicle_number
        }
    else:
        # Clean and structure response
        result = {
            "status": "success",
            "developer": DEVELOPER,
            "credit": CREDIT,
            "vehicle_number": vehicle_number,
            "registration_details": rc_data if rc_data else None,
            "challan_details": challan_data if challan_data else None,
            "timestamp": datetime.now().isoformat()
        }
        
        # Remove empty values
        if result["registration_details"] is None:
            del result["registration_details"]
        if result["challan_details"] is None:
            del result["challan_details"]
    
    # Cache result
    set_to_cache(cache_key, result)
    return result

# ==================== ROUTES ====================

@app.route("/", methods=['GET'])
def index():
    """Home route"""
    return jsonify({
        "status": "online",
        "message": "Premium White-Labeled Vehicle Gateway",
        "developer": DEVELOPER,
        "credit": CREDIT,
        "version": "2.0",
        "endpoints": {
            "/fetch": "GET - Fetch vehicle and challan details",
            "/fetch/rc": "GET - Fetch only registration details",
            "/fetch/challan": "GET - Fetch only challan details",
            "/health": "GET - Health check"
        },
        "usage": "/fetch?vehicle=GJ21DB1119",
        "example": "https://your-domain.vercel.app/fetch?vehicle=GJ21DB1119"
    })

@app.route("/health", methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(cache),
        "developer": DEVELOPER
    })

@app.route("/fetch", methods=['GET'])
def fetch_details():
    """
    Main fetch endpoint - Gets both RC and Challan details
    """
    try:
        # Get vehicle number
        vehicle = request.args.get("vehicle", "").strip().upper()
        if not vehicle:
            return jsonify({
                "status": "error",
                "message": "Vehicle number is required",
                "usage": "/fetch?vehicle=GJ21DB1119"
            }), 400
        
        # Clean vehicle number
        vehicle = re.sub(r'[^A-Z0-9]', '', vehicle)
        if len(vehicle) < 6:
            return jsonify({
                "status": "error",
                "message": "Invalid vehicle number format",
                "vehicle_number": vehicle
            }), 400
        
        # Get cookies from request
        cookies = request.headers.get("X-Vahan-Cookie") or request.args.get("cookies", "")
        
        # Process data
        result = process_vehicle_data(vehicle, cookies)
        
        # Check if we got an error
        if result.get("status") == "error":
            return jsonify(result), 404
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}",
            "developer": DEVELOPER
        }), 500

@app.route("/fetch/rc", methods=['GET'])
def fetch_rc_details():
    """
    Fetch only RC details
    """
    try:
        vehicle = request.args.get("vehicle", "").strip().upper()
        if not vehicle:
            return jsonify({"error": "Vehicle number required"}), 400
        
        vehicle = re.sub(r'[^A-Z0-9]', '', vehicle)
        if len(vehicle) < 6:
            return jsonify({"error": "Invalid vehicle number"}), 400
        
        cookies = request.headers.get("X-Vahan-Cookie") or request.args.get("cookies", "")
        
        # Get full data first
        full_data = process_vehicle_data(vehicle, cookies)
        
        if full_data.get("status") == "error":
            return jsonify(full_data), 404
        
        return jsonify({
            "status": "success",
            "vehicle_number": vehicle,
            "registration_details": full_data.get("registration_details", {}),
            "developer": DEVELOPER,
            "credit": CREDIT
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/fetch/challan", methods=['GET'])
def fetch_challan_details():
    """
    Fetch only Challan details
    """
    try:
        vehicle = request.args.get("vehicle", "").strip().upper()
        if not vehicle:
            return jsonify({"error": "Vehicle number required"}), 400
        
        vehicle = re.sub(r'[^A-Z0-9]', '', vehicle)
        if len(vehicle) < 6:
            return jsonify({"error": "Invalid vehicle number"}), 400
        
        cookies = request.headers.get("X-Vahan-Cookie") or request.args.get("cookies", "")
        
        # Get full data first
        full_data = process_vehicle_data(vehicle, cookies)
        
        if full_data.get("status") == "error":
            return jsonify(full_data), 404
        
        return jsonify({
            "status": "success",
            "vehicle_number": vehicle,
            "challan_details": full_data.get("challan_details", {}),
            "developer": DEVELOPER,
            "credit": CREDIT
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/cache/clear", methods=['POST'])
def clear_cache():
    """Clear the cache (admin only)"""
    # Simple security check
    key = request.headers.get("X-Admin-Key")
    if key != "SB_SAKIB_2024":
        return jsonify({"error": "Unauthorized"}), 401
    
    cache.clear()
    cache_timestamps.clear()
    return jsonify({
        "status": "success",
        "message": "Cache cleared successfully",
        "developer": DEVELOPER
    })

# ==================== ERROR HANDLING ====================

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": ["/", "/fetch", "/fetch/rc", "/fetch/challan", "/health"]
    }), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({
        "error": "Internal server error",
        "developer": DEVELOPER
    }), 500

# ==================== MAIN ====================

if __name__ == "__main__":
    app.run(debug=DEBUG_MODE, host='0.0.0.0', port=5000)