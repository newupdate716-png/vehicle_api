# ============================================
# 🚗 PREMIUM VEHICLE INFO API (Vercel Optimized)
# 👑 Dev: @sakib01994 • 💳 Src: HACKER
# ============================================

from flask import Flask, request, jsonify
import requests
import re
import logging
from bs4 import BeautifulSoup

app = Flask(__name__)

# ==================== CONFIGURATION ====================
DEBUG_MODE = False
REQUEST_TIMEOUT = 25 # Vercel has a 30s limit for hobby tier
DEVELOPER = "@sakib01994"
CREDIT = "SB-SAKIB @sakib01994"

PRIMARY_API_URL = "https://prosnal-vehicle.gauravcyber0.workers.dev/?vehicle={}"
HOMEPAGE_URL = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/statevalidation/homepage.xhtml?statecd=Mzc2MzM2MzAzNjY0MzIzODM3NjIzNjY0MzY2MjM3NDQ0Yw=="
HOMEPAGE_BASE = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/statevalidation/homepage.xhtml"
LOGIN_URL = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/usermgmt/login.xhtml"
FORM_URL = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/balanceservice/form_reschedule_fitness.xhtml"

# Memory Cache (Note: This is temporary in Vercel)
volatile_cache = {}

# ==================== HELPER FUNCTIONS ====================

def extract_viewstate(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    inp = soup.find('input', {'name': 'javax.faces.ViewState'})
    return inp.get('value') if inp else None

def extract_viewstate_from_ajax(text):
    match = re.search(r'<update id="j_id1:javax.faces.ViewState:0"><!\[CDATA\[(.*?)\]\]></update>', text)
    return match.group(1) if match else None

def find_checkbox_id(html_content):
    match = re.search(r'PrimeFaces\.cw\("SelectBooleanCheckbox"[^}]*id:"(j_idt\d+)"', html_content)
    return match.group(1) if match else "j_idt193"

def fetch_vehicle_details(vehicle_number):
    try:
        response = requests.get(PRIMARY_API_URL.format(vehicle_number), timeout=REQUEST_TIMEOUT)
        data = response.json()
        if data.get("status") == "success" and data.get("data"):
            return {"success": True, "data": data.get("data")}
    except:
        pass
    return {"success": False, "error": "Primary API Fetch Failed"}

def fetch_mobile_number(vehicle_number, chassis_last_5):
    try:
        session = requests.Session()
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        headers = {'User-Agent': ua, 'Accept': 'text/html,application/xhtml+xml'}
        
        # Step 1: Get Homepage
        r1 = session.get(HOMEPAGE_URL, headers=headers, timeout=REQUEST_TIMEOUT)
        vs = extract_viewstate(r1.text)
        cid = find_checkbox_id(r1.text)
        
        ajax_headers = {
            'User-Agent': ua,
            'Faces-Request': 'partial/ajax',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://vahan.parivahan.gov.in',
            'Referer': HOMEPAGE_URL
        }

        # Step 2: Select Office
        p2 = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': 'fit_c_office_to',
            'javax.faces.partial.execute': 'fit_c_office_to',
            'homepageformid': 'homepageformid',
            'fit_c_office_to_input': '1',
            'javax.faces.ViewState': vs,
        }
        r2 = session.post(HOMEPAGE_BASE, data=p2, headers=ajax_headers)
        vs = extract_viewstate_from_ajax(r2.text) or vs

        # Step 3: Checkbox and Proceed
        p3 = {'javax.faces.partial.ajax': 'true', 'javax.faces.source': cid, 'homepageformid': 'homepageformid', f'{cid}_input': 'on', 'javax.faces.ViewState': vs}
        r3 = session.post(HOMEPAGE_BASE, data=p3, headers=ajax_headers)
        vs = extract_viewstate_from_ajax(r3.text) or vs

        p4 = {'javax.faces.partial.ajax': 'true', 'javax.faces.source': 'proccedHomeButtonId', 'proccedHomeButtonId': 'proccedHomeButtonId', 'homepageformid': 'homepageformid', f'{cid}_input': 'on', 'javax.faces.ViewState': vs}
        r4 = session.post(HOMEPAGE_BASE, data=p4, headers=ajax_headers)
        vs = extract_viewstate_from_ajax(r4.text) or vs

        # Step 4: Final Dialog & Redirection
        dlg = re.search(r'id="(j_idt\d+)"[^>]*class="[^"]*ui-button', r4.text)
        dlg_btn = dlg.group(1) if dlg else "j_idt536"
        p5 = {'javax.faces.partial.ajax': 'true', 'javax.faces.source': dlg_btn, f'{dlg_btn}': dlg_btn, 'homepageformid': 'homepageformid', 'javax.faces.ViewState': vs}
        session.post(HOMEPAGE_BASE, data=p5, headers=ajax_headers)

        # Step 5: Login Page Logic
        r6 = session.get(LOGIN_URL + "?faces-redirect=true", headers=headers)
        vs = extract_viewstate(r6.text)
        fit_btn = re.search(r'id="(j_idt\d+)"[^>]*type="submit"', r6.text)
        fit = fit_btn.group(1) if fit_btn else "j_idt506"

        p7 = {'loginForm': 'loginForm', f'{fit}': fit, 'javax.faces.ViewState': vs, 'pur_cd': '86'}
        session.post(LOGIN_URL, data=p7, headers=headers)

        # Step 6: Form Data Submit
        r8 = session.get(FORM_URL, headers=headers)
        vs = extract_viewstate(r8.text)

        p9 = {
            'javax.faces.partial.ajax': 'true',
            'javax.faces.source': 'balanceFeesFine:validate_dtls',
            'balanceFeesFine:validate_dtls': 'balanceFeesFine:validate_dtls',
            'balanceFeesFine:tf_reg_no': vehicle_number,
            'balanceFeesFine:tf_chasis_no': chassis_last_5,
            'javax.faces.ViewState': vs,
        }
        r9 = session.post(FORM_URL, data=p9, headers=ajax_headers)
        
        # Final Regex for Mobile Number
        match = re.search(r'value="([6-9]\d{9})"', r9.text)
        if match:
            return {"success": True, "mobile_number": match.group(1)}
        
        return {"success": False, "error": "Mobile not found in response"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== ROUTES ====================

@app.route("/")
def index():
    return jsonify({
        "status": "online",
        "message": "Vehicle Mobile Extracter API",
        "usage": " CONTACT OWNER,, ",
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

    # 1. Fetch Chassis Info
    base_info = fetch_vehicle_details(vehicle)
    if not base_info["success"]:
        return jsonify({"status": "error", "message": base_info["error"]}), 404

    v_data = base_info["data"]
    chassis = v_data.get("vehicle_chasi_number", "")
    chassis_last_5 = chassis[-5:] if len(chassis) >= 5 else chassis

    # 2. Fetch Mobile
    mobile_info = fetch_mobile_number(vehicle, chassis_last_5)
    
    v_data["mobile_number"] = mobile_info["mobile_number"] if mobile_info["success"] else "Not Found"
    
    response_data = {
        "status": "success",
        "developer": DEVELOPER,
        "credit": CREDIT,
        "data": v_data
    }

    # Store in memory cache
    volatile_cache[vehicle] = response_data
    
    return jsonify(response_data)

# Required for Vercel
app.debug = DEBUG_MODE