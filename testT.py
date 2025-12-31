import requests
import time
import random

# ================= কনফিগারেশন =================
URL = "http://127.0.0.1:8000/api/update-location/"
BUS_ID = "BUS-01"
API_KEY = "secret_key" # <--- Django Admin থেকে পাওয়া কী-টি এখানে দিন

# ৫টি স্টপ এবং কোঅর্ডিনেটস
stops = [
    {"name": "Uni Gate", "lat": 23.8103, "lng": 90.4125},
    {"name": "Science", "lat": 23.8150, "lng": 90.4150},
    {"name": "Library", "lat": 23.8200, "lng": 90.4200},
    {"name": "Market", "lat": 23.8250, "lng": 90.4250},
    {"name": "City Center", "lat": 23.8300, "lng": 90.4300},
]

def send_update(lat, lng, direction, msg, speed):
    try:
        # জিপিএস ডাটা ফরম্যাটিং (NMEA-ish format যা আপনার ব্যাকএন্ড পার্স করে)
        d_lat = int(lat)
        m_lat = (lat - d_lat) * 60
        lat_n = f"{d_lat*100+m_lat:.4f}"
        
        d_lng = int(lng)
        m_lng = (lng - d_lng) * 60
        lng_n = f"{d_lng*100+m_lng:.4f}"
        
        gps_raw = f"{lat_n},N,{lng_n},E,123456,123456.0,{speed},8.0,0.0"
        
        # মূল পেলোড যেখানে API_KEY যুক্ত করা হয়েছে
        payload = {
            "bus_id": BUS_ID,
            "api_key": API_KEY,  # <--- নতুন সিকিউরিটি ফিল্ড
            "gps_raw": gps_raw,
            "direction": direction,
            "speed": speed
        }
        
        response = requests.post(URL, json=payload, timeout=2)
        
        if response.status_code == 200:
            icon = "🟢" if direction == "UNI_TO_CITY" else "🔵"
            print(f"{icon} {msg} | 🚀 Speed: {speed} km/h | Status: Success")
        elif response.status_code == 403:
            print("❌ Error: Invalid API Key!")
        else:
            print(f"❌ Error: Server returned {response.status_code}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
    
    time.sleep(2) # ২ সেকেন্ড বিরতি

# ================= সিমুলেশন শুরু =================

print(f"🚌 Starting Bus Simulation for {BUS_ID}")
print(f"🔑 Using API Key: {API_KEY[:5]}*****")

# ১. ফরওয়ার্ড ট্রিপ (UNI → CITY)
print("\n➡️  DIRECTION: UNI_TO_CITY (Starting Trip)")
for i, stop in enumerate(stops):
    rand_speed = random.randint(25, 55) if i < len(stops)-1 else 0
    send_update(stop['lat'], stop['lng'], "UNI_TO_CITY", f"Stop {i+1}: {stop['name']}", rand_speed)

# ২. ডিরেকশন চেঞ্জ (টার্মিনালে ওয়েটিং)
print("\n🔄 CHANGING DIRECTION...")
time.sleep(1)
send_update(stops[-1]['lat'], stops[-1]['lng'], "CITY_TO_UNI", "Terminal: Direction Switched", 0)

# ৩. রিটার্ন ট্রিপ (CITY → UNI)
print("\n⬅️  DIRECTION: CITY_TO_UNI (Returning)")
for i in range(len(stops)-1, -1, -1):
    rand_speed = random.randint(20, 50) if i > 0 else 0
    send_update(stops[i]['lat'], stops[i]['lng'], "CITY_TO_UNI", f"Return Stop: {stops[i]['name']}", rand_speed)

print("\n✅ Simulation Completed!")