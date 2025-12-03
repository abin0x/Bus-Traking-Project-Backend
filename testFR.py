import requests
import time

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

def send(lat, lng, direction, msg):
    try:
        # Convert to NMEA
        d = int(lat)
        m = (lat - d) * 60
        lat_n = f"{d*100+m:.4f}"
        
        d = int(lng)
        m = (lng - d) * 60
        lng_n = f"{d*100+m:.4f}"
        
        gps = f"{lat_n},N,{lng_n},E,123456,123456.0,10.0,8.0,0.0"
        
        requests.post(URL, json={
            "bus_id": BUS_ID,
            "gps_raw": gps,
            "direction": direction
        }, timeout=1)
        
        icon = "🟢" if direction == "UNI_TO_CITY" else "🔵"
        print(f"{icon} {msg}")
    except:
        print("❌ Error")
    
    time.sleep(2)  # 2 seconds between sends

print("🚌 Quick Simulation - 5 Stops")

# Forward trip (UNI → CITY)
print("\n➡️  UNI_TO_CITY")
for i, stop in enumerate(stops):
    send(stop['lat'], stop['lng'], "UNI_TO_CITY", f"Stop {i+1}: {stop['name']}")

# Change direction at last stop
print("\n🔄 DIRECTION CHANGE")
send(stops[-1]['lat'], stops[-1]['lng'], "CITY_TO_UNI", "Switch to CITY_TO_UNI")

# Return trip (CITY → UNI)
print("\n⬅️  CITY_TO_UNI")
for i in range(len(stops)-1, -1, -1):
    send(stops[i]['lat'], stops[i]['lng'], "CITY_TO_UNI", f"Return Stop {len(stops)-i}: {stops[i]['name']}")

print("\n✅ Done!")