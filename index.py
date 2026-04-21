# ============================================
# 🚗 PREMIUM VEHICLE INFO API (Vercel Optimized)
# 👑 Dev: @sakib01994 • 💳 Src: HACKER
# ============================================

from flask import Flask, request, jsonify
import requests
import re
from bs4 import BeautifulSoup

app = Flask(__name__)

# ==================== CONFIGURATION ====================
DEBUG_MODE = False
REQUEST_TIMEOUT = 25
DEVELOPER = "@sakib01994"
CREDIT = "SB-SAKIB @sakib01994"

PRIMARY_API_URL = "https://prosnal-vehicle.gauravcyber0.workers.dev/?vehicle={}"
VAHANX_URL = "https://vahanx.in/rc-search/{}"

# Memory Cache (Temporary)
volatile_cache = {}

# ==================== HELPER FUNCTIONS ====================

def fetch_from_vahanx(vehicle_number):
    """
    আপনার দেওয়া PHP লজিক অনুযায়ী VahanX থেকে ডেটা স্ক্র্যাপ করার ফাংশন
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://vahanx.in/'
        }
        response = requests.get(VAHANX_URL.format(vehicle_number), headers=headers, timeout=15)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # RTO ফোন নম্বর খোঁজার চেষ্টা (আপনার PHP কোড অনুযায়ী)
        # সাধারণত 'Phone' লেবেলের পাশের টেক্সটটি খোঁজা হচ্ছে
        phone = None
        phone_nodes = soup.find_all("span", string=re.compile("Phone", re.I))
        for node in phone_nodes:
            parent = node.parent
            p_tag = parent.find("p")
            if p_tag:
                phone = p_tag.get_text(strip=True)
                break
        
        return phone
    except:
        return None

def fetch_vehicle_details(vehicle_number):
    try:
        response = requests.get(PRIMARY_API_URL.format(vehicle_number), timeout=REQUEST_TIMEOUT)
        data = response.json()
        if data.get("status") == "success" and data.get("data"):
            return {"success": True, "data": data.get("data")}
    except:
        pass
    return {"success": False, "error": "Primary API Fetch Failed"}

# ==================== ROUTES ====================

@app.route("/")
def index():
    return jsonify({
        "status": "online",
        "message": "Vehicle Mobile Extracter API",
        "usage": "/fetch?vehicle=REG_NUMBER",
        "owner": DEVELOPER
    })

@app.route("/fetch", methods=["GET"])
def fetch():
    vehicle = request.args.get("vehicle", "").strip().upper()
    vehicle = re.sub(r'[^A-Z0-9]', '', vehicle)

    if not vehicle or len(vehicle) < 6:
        return jsonify({"status": "error", "message": "Invalid Vehicle Number"}), 400

    # ক্যাশ চেক
    if vehicle in volatile_cache:
        return jsonify(volatile_cache[vehicle])

    # ১. প্রাইমারি এপিআই থেকে মেইন ডেটা সংগ্রহ
    base_info = fetch_vehicle_details(vehicle)
    if not base_info["success"]:
        return jsonify({"status": "error", "message": base_info["error"]}), 404

    v_data = base_info["data"]
    
    # ২. ফোন নম্বর বের করার জন্য সেকেন্ডারি সোর্স (VahanX) ব্যবহার
    # যদি প্রাইমারি ডেটায় মোবাইল নম্বর না থাকে বা 'Not Available' থাকে
    found_mobile = fetch_from_vahanx(vehicle)
    
    if found_mobile:
        v_data["mobile_number"] = found_mobile
    else:
        # যদি কোথাও না পাওয়া যায় তবে আগের মতই থাকবে
        if "mobile_number" not in v_data:
            v_data["mobile_number"] = "Not Found"

    response_data = {
        "status": "success",
        "developer": DEVELOPER,
        "credit": CREDIT,
        "data": v_data
    }

    # মেমোরি ক্যাশে সেভ করা (একই রিকোয়েস্ট বারবার আসলে ফাস্ট হবে)
    volatile_cache[vehicle] = response_data
    
    return jsonify(response_data)

if __name__ == "__main__":
    app.run(debug=DEBUG_MODE)
