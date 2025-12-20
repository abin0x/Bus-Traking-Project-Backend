import requests
import time
import random

URL = "http://127.0.0.1:8000/api/update-location/"
BUS_ID = "BUS-01"

# Updated stops for HSTU route (City → Uni direction)
# Starting from city side (HSTU Bus Terminal) to university side (Boromath)
stops = [
    {"name": "HSTU Bus Terminal", "lat": 25.697721, "lng": 88.65489},
    {"name": "Gopalganj", "lat": 25.674047, "lng": 88.652051},
    {"name": "College Mor", "lat": 25.651059, "lng": 88.646528},
    {"name": "Terminal", "lat": 25.643882, "lng": 88.647428},
    {"name": "Moharajar Mor", "lat": 25.62624, "lng": 88.63711},
    {"name": "Hospital Mor", "lat": 25.622493, "lng": 88.635196},
    {"name": "Boromath", "lat": 25.622493, "lng": 88.635196},  # Assuming this is the university endpoint
]

def send(lat, lng, direction, msg, speed):
    try:
        # Convert decimal degrees to NMEA format (DDMM.mmmm)
        d = int(abs(lat))
        m = (abs(lat) - d) * 60
        lat_n = f"{d:02d}{m:07.4f}"  # Improved formatting for proper NMEA
        lat_dir = "N" if lat >= 0 else "S"
        
        d = int(abs(lng))
        m = (abs(lng) - d) * 60
        lng_n = f"{d:03d}{m:07.4f}"
        lng_dir = "E" if lng >= 0 else "W"
        
        # gps_raw format: lat,NS,lon,EW,... (using placeholders for others)
        gps = f"{lat_n},{lat_dir},{lng_n},{lng_dir},123456,123456.0,{speed},8.0,0.0"
        
        requests.post(URL, json={
            "bus_id": BUS_ID,
            "gps_raw": gps,
            "direction": direction,
            "speed": speed
        }, timeout=1)
        
        icon = "🟢" if direction == "CITY_TO_UNI" else "🔵"
        print(f"{icon} {msg} | Speed: {speed} km/h | Lat: {lat}, Lng: {lng}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    time.sleep(2)

print("🚌 HSTU Bus Route Simulation with Real Stops")

# Forward trip: City → University
print("\n➡️  CITY_TO_UNI")
for i, stop in enumerate(stops):
    current_speed = random.randint(10, 40)
    send(stop['lat'], stop['lng'], "CITY_TO_UNI", f"Stop {i+1}: {stop['name']}", current_speed)

# Direction change at university end
print("\n🔄 DIRECTION CHANGE AT UNIVERSITY")
send(stops[-1]['lat'], stops[-1]['lng'], "UNI_TO_CITY", "Switching to UNI_TO_CITY", 0)

# Return trip: University → City (reverse order)
print("\n⬅️  UNI_TO_CITY")
for i in range(len(stops)-1, -1, -1):
    current_speed = random.randint(10, 40)
    send(stops[i]['lat'], stops[i]['lng'], "UNI_TO_CITY", f"Return Stop {len(stops)-i}: {stops[i]['name']}", current_speed)

print("\n✅ Simulation Complete!")