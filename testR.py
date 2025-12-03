import requests
import time

URL = "http://127.0.0.1:8000/api/update-location/"
BUS_ID = "BUS-01"

# University Terminal Coordinates
TERMINAL_LAT = 23.8103
TERMINAL_LNG = 90.4125

def send_data(lat, lng, speed_kmh, status_msg):
    try:
        # Coordinate Conversion (Decimal to NMEA)
        d_lat = int(lat)
        m_lat = (lat - d_lat) * 60
        lat_nmea = f"{d_lat*100+m_lat:.4f}"
        
        d_lng = int(lng)
        m_lng = (lng - d_lng) * 60
        lng_nmea = f"{d_lng*100+m_lng:.4f}"
        
        # Speed Conversion (Km/h to Knots)
        speed_knots = speed_kmh / 1.852
        
        # NMEA String Construction
        gps = f"{lat_nmea},N,{lng_nmea},E,123456,123456.0,10.0,{speed_knots:.1f},0.0"
        
        response = requests.post(URL, json={
            "bus_id": BUS_ID,
            "gps_raw": gps,
            "direction": "STOPPED" # ড্রাইভার বাটন চাপছে না
        })
        
        print(f"{status_msg} | Speed: {speed_kmh} km/h | Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

print("🧪 TEST: READY STATE & DEPARTURE LOGIC")
print("=======================================")

# Step 1: Arriving at Terminal (Moving)
print("\n1️⃣  Arriving at Terminal...")
send_data(TERMINAL_LAT, TERMINAL_LNG, 15.0, "🚌 Approaching")
time.sleep(2)

# Step 2: Stopped at Terminal (Should trigger READY)
print("\n2️⃣  Stopped at Terminal (Waiting for Passengers)...")
for i in range(5):
    send_data(TERMINAL_LAT, TERMINAL_LNG, 0.0, f"🛑 Stopped ({i+1}/5)")
    time.sleep(2)

# Step 3: Leaving Terminal (Should trigger ON_TRIP)
print("\n3️⃣  Leaving Terminal (Speeding up)...")
# Move slightly away
send_data(TERMINAL_LAT + 0.0005, TERMINAL_LNG + 0.0005, 10.0, "🚀 Departure started")
time.sleep(2)
send_data(TERMINAL_LAT + 0.0010, TERMINAL_LNG + 0.0010, 25.0, "🚀 On Main Road")

print("\n✅ Test Finished! Check Dashboard for Yellow to Green transition.")