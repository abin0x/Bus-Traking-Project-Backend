import requests
import time
import random
import json

# সার্ভারের ঠিকানা
URL = "http://127.0.0.1:8000/api/update-location/"

# ঢাকার জিপিএস কোঅর্ডিনেট (মিরপুর এরিয়া)
lat = 23.8103
lng = 90.4125

print("🚌 Bus Simulation Started (SIM7600 Style)...")
print(f"Target URL: {URL}")

# SIM7600 এর মতো DDMM.MMMM ফরম্যাট বানানোর হেল্পার ফাংশন
def to_nmea_format(degrees):
    d = int(degrees)
    m = (degrees - d) * 60
    # ফরম্যাট: DDMM.MMMM (যেমন: 2352.1234)
    return f"{d * 100 + m:.4f}"

while True:
    # ১. বাস একটু একটু করে সরছে (Simulating Movement)
    lat += 0.0002
    lng += 0.0002
    
    # স্পিড র‍্যান্ডমলি পরিবর্তন হচ্ছে
    speed_kmh = random.randint(5, 45) 
    # SIM7600 স্পিড Knots এ দেয়, তাই কনভার্ট করে স্ট্রিং বানাচ্ছি
    speed_knots = speed_kmh / 1.852 

    # ২. জিপিএস র স্ট্রিং তৈরি (SIM7600 Format)
    # Format: lat,N,lon,E,date,time,alt,speed,course
    lat_nmea = to_nmea_format(lat)
    lng_nmea = to_nmea_format(lng)
    
    # এটি হুবহু আপনার ডিভাইসের আউটপুটের মতো বানানো হলো
    gps_raw_string = f"{lat_nmea},N,{lng_nmea},E,021225,123456.0,10.0,{speed_knots:.1f},0.0"

    # ৩. ডেটা প্যাকেট তৈরি (Updated JSON Structure)
    payload = {
        "bus_id": "BUS-01",        # আপডেট: device_id এর বদলে bus_id
        "gps_raw": gps_raw_string, # আপডেট: রিয়েল NMEA স্ট্রিং
        "direction": "CITY_TO_UNI",  # স্থির ডিরেকশন
        "type": "location_update"
    }

    try:
        # ৪. HTTP POST রিকোয়েস্ট পাঠানো
        start_time = time.time()
        response = requests.post(URL, json=payload)
        end_time = time.time()
        
        duration = round((end_time - start_time) * 1000, 2)

        if response.status_code == 200:
            print(f"✅ Sent: {speed_kmh}km/h {lat_nmea} and {lng_nmea} | Server: 200 OK ({duration}ms)")
        else:
            print(f"⚠️ Server Error: {response.status_code} | Msg: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Connection Error! Make sure Django server is running.")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 10 সেকেন্ড পর পর আপডেট (ডিভাইসের মতোই)
    time.sleep(10)