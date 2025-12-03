import requests
import time

URL = "http://127.0.0.1:8000/api/update-location/"
BUS_ID = "BUS-02"

# Middle of the road coordinates (Not terminal)
# MIDDLE_LAT = 23.8103
# MIDDLE_LNG = 90.4125
MIDDLE_LAT = 23.8200
MIDDLE_LNG = 90.4200

def send_data(lat, lng, speed_kmh, msg):
    d_lat = int(lat)
    m_lat = (lat - d_lat) * 60
    lat_nmea = f"{d_lat*100+m_lat:.4f}"
    
    d_lng = int(lng)
    m_lng = (lng - d_lng) * 60
    lng_nmea = f"{d_lng*100+m_lng:.4f}"
    
    speed_knots = speed_kmh / 1.852
    gps = f"{lat_nmea},N,{lng_nmea},E,123456,123456.0,10.0,{speed_knots:.1f},0.0"
    
    requests.post(URL, json={
        "bus_id": BUS_ID,
        "gps_raw": gps,
        "direction": "UNI_TO_CITY"
    })
    print(msg)

print("🧪 TEST: TRAFFIC JAM LOGIC")
print("=======================================")

# 1. Moving normally
print("1️⃣  Bus Moving...")
send_data(MIDDLE_LAT, MIDDLE_LNG, 30.0, "🚌 Moving at 30km/h")
time.sleep(2)

# 2. Stuck in Traffic (Speed 0, but NOT at terminal)
print("\n2️⃣  Stuck in Traffic (Speed 0)...")
for i in range(4):
    send_data(MIDDLE_LAT, MIDDLE_LNG, 0.0, f"⚠️  Traffic Jam ({i+1}/4) - Should stay ON_TRIP")
    time.sleep(2)

# 3. Moving again
print("\n3️⃣  Traffic Cleared...")
send_data(MIDDLE_LAT + 0.001, MIDDLE_LNG + 0.001, 35.0, "🚀 Moving again")

print("\n✅ Test Finished! Dashboard should show RED traffic line but stay ON TRIP.")