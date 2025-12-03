import requests
import time

URL = "http://127.0.0.1:8000/api/update-location/"
BUS_ID = "BUS-02"

# স্টপ লিস্ট
s1 = {"lat": 23.8103, "lng": 90.4125}
s2 = {"lat": 23.8150, "lng": 90.4150}
s3 = {"lat": 23.8200, "lng": 90.4200}

def to_nmea(deg):
    d = int(deg)
    m = (deg - d) * 60
    return f"{d * 100 + m:.4f}"

def send_data(lat, lng, direction, msg):
    lat_n = to_nmea(lat)
    lng_n = to_nmea(lng)
    gps = f"{lat_n},N,{lng_n},E,123456,123456.0,10.0,15.5,0.0"
    
    payload = {
        "bus_id": BUS_ID, "gps_raw": gps, "direction": direction
    }
    try:
        requests.post(URL, json=payload)
        print(f"📡 {msg} ({direction})")
    except:
        print("Error")

# --- PART 1: GOING ---
print("\n--- 🚀 JAWA SHURU (UNI -> CITY) ---")
send_data(s1['lat'], s1['lng'], "UNI_TO_CITY", "At Stop 1")
time.sleep(3)
send_data(s2['lat'], s2['lng'], "UNI_TO_CITY", "At Stop 2")
time.sleep(3)
send_data(s3['lat'], s3['lng'], "UNI_TO_CITY", "At Stop 3 (Last Stop)")
time.sleep(3)

# --- PART 2: SWITCHING ---
print("\n--- 🔄 DIRECTION CHANGING ---")
# বাস এখন স্টপ ৩ এ আছে কিন্তু বাটন চাপল উল্টো আসার জন্য
send_data(s3['lat'], s3['lng'], "CITY_TO_UNI", "Switching at Stop 3") 
time.sleep(3)

# --- PART 3: RETURNING ---
print("\n--- 🏠 FERA SHURU (CITY -> UNI) ---")
send_data(s2['lat'], s2['lng'], "CITY_TO_UNI", "Back at Stop 2")
time.sleep(3)
send_data(s1['lat'], s1['lng'], "CITY_TO_UNI", "Back at Stop 1")