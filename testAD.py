import requests
import time

URL = "http://127.0.0.1:8000/api/update-location/"
BUS_ID = "BUS-02"

# Route Points
CITY_POINT = {"lat": 23.8300, "lng": 90.4300} # End
UNI_POINT = {"lat": 23.8103, "lng": 90.4125}  # Start

def send_data(lat, lng, direction_header, msg):
    d_lat = int(lat)
    m_lat = (lat - d_lat) * 60
    lat_nmea = f"{d_lat*100+m_lat:.4f}"
    
    d_lng = int(lng)
    m_lng = (lng - d_lng) * 60
    lng_nmea = f"{d_lng*100+m_lng:.4f}"
    
    gps = f"{lat_nmea},N,{lng_nmea},E,123456,123456.0,10.0,15.0,0.0" # Speed 27 km/h
    
    # Notice we are sending the WRONG direction or STOPPED
    requests.post(URL, json={
        "bus_id": BUS_ID,
        "gps_raw": gps,
        "direction": direction_header 
    })
    print(msg)

print("🧪 TEST: AUTO DIRECTION SWITCH")
print("=======================================")

# Scenario: Bus is at CITY (End), Driver forgot to change button.
# Driver starts driving towards UNI, but button says STOPPED or UNI_TO_CITY (Wrong)

print("1️⃣  Bus at CITY (End Terminal)...")
# Send a few updates at City
send_data(CITY_POINT['lat'], CITY_POINT['lng'], "STOPPED", "🛑 At City Terminal")
time.sleep(2)

print("\n2️⃣  Driving towards UNI (But driver didn't press button)...")
# Creating a path from City towards Uni
lat = CITY_POINT['lat']
lng = CITY_POINT['lng']

for i in range(5):
    # Decreasing coordinates (Moving South-West towards Uni)
    lat -= 0.002
    lng -= 0.002
    
    # We send "STOPPED" to force auto-detection
    send_data(lat, lng, "STOPPED", f"🚌 Moving towards UNI... ({i+1}/5)")
    time.sleep(2)

print("\n✅ Test Finished! Check console logs. Server should print 'Auto-Switch: Leaving City -> Uni'")