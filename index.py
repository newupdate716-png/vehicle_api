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

# আপনার দেওয়া সেই মেইন এপিআই যা থেকে সব ডেটা আসে
PRIMARY_API_URL = "https://prosnal-vehicle.gauravcyber0.workers.dev/?vehicle={}"
# আপনার দেওয়া পিএইচপি লজিকের সোর্স সাইট
VAHANX_BASE_URL = "https://vahanx.in/rc-search/{}"

# ==================== HELPER FUNCTIONS ====================

def fetch_mobile_from_vahanx(vehicle_number):
    """
    আপনার দেওয়া PHP কোড থেকে এই লজিকটি নেওয়া হয়েছে।
    এটি VahanX সাইট থেকে স্ক্র্যাপ করে মোবাইল নম্বর বের করে।
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://vahanx.in/'
        }
        # VahanX এ রিকোয়েস্ট পাঠানো হচ্ছে
        response = requests.get(VAHANX_BASE_URL.format(vehicle_number), headers=headers, timeout=15)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # আপনার PHP-তে 'Phone' ফিল্ডটি খোঁজা হচ্ছিল
        # আমরা এখানে regex দিয়ে মোবাইল নম্বর বা ফোন ফিল্ডটি খুঁজছি
        # VahanX এর HTML স্ট্রাকচার অনুযায়ী মোবাইল নম্বর খোঁজা হচ্ছে
        mobile = None
        
        # ১. সরাসরি লেবেল দিয়ে খোঁজা (যেমন PHP তে ছিল)
        phone_labels = soup.find_all(string=re.compile("Phone", re.I))
        for label in phone_labels:
            parent = label.parent.parent # p বা div এ যাওয়ার জন্য
            text = parent.get_text()
            match = re.search(r'\d{10}', text)
            if match:
                mobile = match.group(0)
                break
        
        # ২. যদি না পাওয়া যায়, তবে সব ১০ ডিজিটের নম্বর খোঁজা
        if not mobile:
            numbers = re.findall(r'\b[6-9]\d{9}\b', response.text)
            if numbers:
                mobile = numbers[0]
                
        return mobile
    except:
        return None

# ==================== MAIN ROUTES ====================

@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "message": "Vehicle Information API",
        "developer": DEVELOPER,
        "credit": CREDIT
    })

@app.route("/fetch", methods=["GET"])
def fetch_vehicle():
    vehicle = request.args.get("vehicle", "").strip().upper()
    vehicle = re.sub(r'[^A-Z0-9]', '', vehicle)

    if not vehicle or len(vehicle) < 6:
        return jsonify({
            "status": "error", 
            "message": "Invalid vehicle number",
            "developer": DEVELOPER
        }), 400

    try:
        # ১. আগের মেইন এপিআই থেকে গাড়ির সব তথ্য নিয়ে আসা
        main_res = requests.get(PRIMARY_API_URL.format(vehicle), timeout=REQUEST_TIMEOUT)
        main_json = main_res.json()

        if main_json.get("status") != "success":
            return jsonify({
                "status": "error",
                "message": "Vehicle data not found in primary source",
                "developer": DEVELOPER
            }), 404

        v_data = main_json.get("data", {})

        # ২. আপনার দেওয়া PHP লজিক অনুযায়ী মোবাইল নম্বর খুঁজে বের করা
        mobile_number = fetch_mobile_from_vahanx(vehicle)

        # ৩. মেইন ডেটাতে মোবাইল নম্বরটি আপডেট করে দেওয়া
        # যাতে আগের রেসপন্স স্টাইল ঠিক থাকে
        v_data["Mobile Number"] = mobile_number if mobile_number else "Not Available"
        
        # ফাইনাল রেসপন্স (হুবহু আগের মতই)
        return jsonify({
            "status": "success",
            "data": v_data,
            "developer": DEVELOPER,
            "credit": CREDIT
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "developer": DEVELOPER
        }), 500

# Vercel এর জন্য প্রয়োজনীয়
if __name__ == "__main__":
    app.run(debug=False)
