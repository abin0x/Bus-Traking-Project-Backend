import requests
import time
import random

URL = "http://127.0.0.1:8000/api/update-location/"
BUS_ID = "BUS-01"

# Stops with coordinates
stops = [
    {"name": "Uni Gate", "lat": 23.8103, "lng": 90.4125},
    {"name": "Science", "lat": 23.8150, "lng": 90.4150},
    {"name": "Library", "lat": 23.8200, "lng": 90.4200},
    {"name": "Market", "lat": 23.8250, "lng": 90.4250},
    {"name": "City Center", "lat": 23.8300, "lng": 90.4300},
    {"name": "Uni Gate", "lat": 23.8350, "lng": 90.4350},
    {"name": "Uni Gate", "lat": 23.8400, "lng": 90.4400},
]

# এখানে speed প্যারামিটার যোগ করা হয়েছে
def send(lat, lng, direction, msg, speed):
    try:
        # Convert to NMEA
        d = int(lat)
        m = (lat - d) * 60
        lat_n = f"{d*100+m:.4f}"
        
        d = int(lng)
        m = (lng - d) * 60
        lng_n = f"{d*100+m:.4f}"
        
        # আগে এখানে 10.0 ফিক্সড ছিল, এখন {speed} ডাইনামিক করা হয়েছে
        gps = f"{lat_n},N,{lng_n},E,123456,123456.0,{speed},8.0,0.0"
        
        requests.post(URL, json={
            "bus_id": BUS_ID,
            "gps_raw": gps,
            "direction": direction,
            "speed": speed  # ব্যাকএন্ডে আলাদাভাবে স্পিড পাঠানো হচ্ছে
        }, timeout=1)
        
        icon = "🟢" if direction == "UNI_TO_CITY" else "🔵"
        print(f"{icon} {msg} | Speed: {speed} km/h")
    except:
        print("❌ Error")
    
    time.sleep(2)

print("🚌 Quick Simulation - 5 Stops with Speed")

# Forward trip (UNI → CITY)
print("\n➡️  UNI_TO_CITY")
for i, stop in enumerate(stops):
    # রেন্ডম স্পিড জেনারেট করা হচ্ছে (১০ থেকে ৪০ এর মধ্যে)
    current_speed = random.randint(10, 40)
    send(stop['lat'], stop['lng'], "UNI_TO_CITY", f"Stop {i+1}: {stop['name']}", current_speed)

# Change direction
print("\n🔄 DIRECTION CHANGE")
send(stops[-1]['lat'], stops[-1]['lng'], "CITY_TO_UNI", "Switch to CITY_TO_UNI", 0)

# Return trip (CITY → UNI)
print("\n⬅️  CITY_TO_UNI")
for i in range(len(stops)-1, -1, -1):
    current_speed = random.randint(10, 40)
    send(stops[i]['lat'], stops[i]['lng'], "CITY_TO_UNI", f"Return Stop {len(stops)-i}: {stops[i]['name']}", current_speed)

# dfdfjdlsdlfdalfda;daskfaf/kdfk
print("\n✅ Done!")