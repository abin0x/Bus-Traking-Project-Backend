import requests
import time
import random  # ১. random ইম্পোর্ট করা হলো

URL = "http://127.0.0.1:8000/api/update-location/"
BUS_ID = "BUS-01"

# 5 stops with your coordinates
stops = [
    {"name": "Uni Gate", "lat": 23.8103, "lng": 90.4125},
    {"name": "Science", "lat": 23.8150, "lng": 90.4150},
    {"name": "Library", "lat": 23.8200, "lng": 90.4200},
    {"name": "Market", "lat": 23.8250, "lng": 90.4250},
    {"name": "City Center", "lat": 23.8300, "lng": 90.4300},
    {"name": "Uni Gate", "lat": 23.8350, "lng": 90.4350},
    {"name": "Uni Gate", "lat": 23.8400, "lng": 90.4400},
]

def send(lat, lng, direction, msg, speed):
    try:
        # Convert to NMEA
        d = int(lat)
        m = (lat - d) * 60
        lat_n = f"{d*100+m:.4f}"
        
        d = int(lng)
        m = (lng - d) * 60
        lng_n = f"{d*100+m:.4f}"
        
        # ২. ফিক্সড 10.0 এর বদলে {speed} বসানো হলো
        gps = f"{lat_n},N,{lng_n},E,123456,123456.0,{speed},8.0,0.0"
        
        requests.post(URL, json={
            "bus_id": BUS_ID,
            "gps_raw": gps,
            "direction": direction,
            "speed": speed  # ব্যাকএন্ডে স্পিড ফিল্ড পাঠানো হচ্ছে
        }, timeout=1)
        
        icon = "🟢" if direction == "UNI_TO_CITY" else "🔵"
        print(f"{icon} {msg} | 🚀 Speed: {speed} km/h")
    except:
        print("❌ Error")
    
    time.sleep(2)  # 2 seconds between sends

print("🚌 Quick Simulation - 5 Stops with Random Speed")

# Forward trip (UNI → CITY)
print("\n➡️  UNI_TO_CITY")
for i, stop in enumerate(stops):
    # ৩. র‍্যান্ডম স্পিড জেনারেট (20-60 km/h)
    rand_speed = random.randint(20, 60)
    send(stop['lat'], stop['lng'], "UNI_TO_CITY", f"Stop {i+1}: {stop['name']}", rand_speed)

# Change direction at last stop (থামলে স্পিড ০)
print("\n🔄 DIRECTION CHANGE")
send(stops[-1]['lat'], stops[-1]['lng'], "CITY_TO_UNI", "Switch to CITY_TO_UNI", 0)

# Return trip (CITY → UNI)
print("\n⬅️  CITY_TO_UNI")
for i in range(len(stops)-1, -1, -1):
    rand_speed = random.randint(10, 60)
    send(stops[i]['lat'], stops[i]['lng'], "CITY_TO_UNI", f"Return Stop {len(stops)-i}: {stops[i]['name']}", rand_speed)

print("\n✅ Done!")# Stops with coordinates
