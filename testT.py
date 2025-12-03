import requests
import time
import sys

# ==========================================
# CONFIGURATION
# ==========================================
URL = "http://127.0.0.1:8000/api/update-location/"

# ⚠️ নিশ্চিত করুন এই ID টি আপনার Django Admin প্যানেলে সেভ করা আছে
BUS_ID = "BUS-01" 

MIDDLE_LAT, MIDDLE_LNG = 23.8200, 90.4200 # Middle of Route
CITY_LAT, CITY_LNG = 23.8300, 90.4300 # End Terminal

def generate_gps(lat, lng, speed_kmh):
    lat_deg = int(lat)
    lat_min = (lat - lat_deg) * 60
    lat_nmea = f"{lat_deg*100+lat_min:.4f}"
    
    lng_deg = int(lng)
    lng_min = (lng - lng_deg) * 60
    lng_nmea = f"{lng_deg*100+lng_min:.4f}"
    
    speed_knots = speed_kmh / 1.852
    return f"{lat_nmea},N,{lng_nmea},E,123456,123456.0,10.0,{speed_knots:.1f},0.0"

def send_request(payload, scenario_name):
    try:
        response = requests.post(URL, json=payload)
        
        # 1. Check HTTP Status
        if response.status_code != 200:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return None

        resp_data = response.json()

        # 2. Check for API Errors (e.g., Device not registered)
        if 'status' in resp_data and resp_data['status'] == 'error':
            print(f"⚠️ API Error in [{scenario_name}]: {resp_data.get('message')}")
            print(f"   👉 Solution: Check if '{payload['bus_id']}' exists in Django Admin.")
            return None
            
        # 3. Check if 'trip_status' key exists
        if 'trip_status' not in resp_data:
            print(f"⚠️ Unexpected Response in [{scenario_name}]: {resp_data}")
            return None

        return resp_data

    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Is the Django server running?")
        sys.exit()
    except Exception as e:
        print(f"❌ Python Error: {e}")
        return None

def run_test():
    print(f"\n🧪 TEST 3: Traffic vs Terminal Logic (Bus: {BUS_ID})")
    print("-" * 60)

    # ==========================================
    # SCENARIO A: TRAFFIC JAM
    # ==========================================
    print("\n[A] Traffic Jam Simulation (Middle of road)")
    print("👉 Action: Bus stops (Speed 0) far from terminals...")
    
    payload_a = {
        "bus_id": BUS_ID,
        "gps_raw": generate_gps(MIDDLE_LAT, MIDDLE_LNG, 0), # Speed 0
        "direction": "STOPPED"
    }
    
    resp_a = send_request(payload_a, "Traffic Jam")

    if resp_a:
        print(f"   Location: Middle | Speed: 0")
        print(f"   Result Status: {resp_a.get('trip_status')}")
        
        if resp_a['trip_status'] == 'ON_TRIP':
            print("✅ PASS: Traffic Jam detected (Status stayed ON_TRIP).")
        else:
            print(f"❌ FAIL: Wrong status for Traffic Jam. Got: {resp_a['trip_status']}")

    time.sleep(2)

    # ==========================================
    # SCENARIO B: TERMINAL ARRIVAL
    # ==========================================
    print("\n[B] Terminal Arrival Simulation (City End)")
    print("👉 Action: Bus stops (Speed 0) at City Terminal...")
    
    payload_b = {
        "bus_id": BUS_ID,
        "gps_raw": generate_gps(CITY_LAT, CITY_LNG, 0), # Speed 0
        "direction": "STOPPED" # Driver forgot button
    }
    
    resp_b = send_request(payload_b, "Terminal Arrival")
    
    if resp_b:
        print(f"   Location: City Terminal | Speed: 0")
        print(f"   Result Status: {resp_b.get('trip_status')}")
        print(f"   Auto Direction: {resp_b.get('direction_status')}")
        
        # Check Logic
        status_ok = resp_b['trip_status'] == 'READY'
        direction_ok = resp_b['direction_status'] == 'CITY_TO_UNI'
        
        if status_ok and direction_ok:
            print("✅ PASS: Auto-detected Terminal & Switched Direction.")
        else:
            print(f"❌ FAIL: Logic failed.")
            print(f"   Expected: READY & CITY_TO_UNI")
            print(f"   Got: {resp_b['trip_status']} & {resp_b.get('direction_status')}")

if __name__ == "__main__":
    run_test()