# import math

# def sim7600_nmea_to_decimal(raw_value, direction):
#     if not raw_value or raw_value == '':
#         return 0.0

#     try:
#         val = float(raw_value)
#         degrees = int(val / 100)
#         minutes = val - (degrees * 100)
#         decimal_val = degrees + (minutes / 60)
#         if direction in ['S', 'W']:
#             decimal_val = -decimal_val
#         return round(decimal_val, 6) 
        
#     except Exception:
#         return 0.0

# def parse_sim7600_gps(raw_string):
#     if not raw_string or "SEARCHING" in raw_string or "ERROR" in raw_string:
#         return None

#     try:
#         parts = raw_string.split(',')
        
#         if len(parts) < 8:
#             return None

#         lat_raw = parts[0] 
#         lat_dir = parts[1] 
#         lon_raw = parts[2] 
#         lon_dir = parts[3] 
        
#         latitude = sim7600_nmea_to_decimal(lat_raw, lat_dir)
#         longitude = sim7600_nmea_to_decimal(lon_raw, lon_dir)
#         speed_knots = float(parts[7]) if parts[7] else 0.0
#         speed_kmh = speed_knots * 1.852
#         if latitude == 0.0 or longitude == 0.0:
#             return None

#         return {
#             'latitude': latitude,
#             'longitude': longitude,
#             'speed': round(speed_kmh, 2)
#         }

#     except Exception as e:
#         print(f"GPS Parsing Error: {e}")
#         return None

# def calculate_distance(lat1, lon1, lat2, lon2):
#     R = 6371000  

#     try:
#         phi1 = math.radians(lat1)
#         phi2 = math.radians(lat2)
#         delta_phi = math.radians(lat2 - lat1)
#         delta_lambda = math.radians(lon2 - lon1)

#         a = math.sin(delta_phi / 2.0) ** 2 + \
#             math.cos(phi1) * math.cos(phi2) * \
#             math.sin(delta_lambda / 2.0) ** 2

#         c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

#         distance_meters = R * c
#         return round(distance_meters, 2)
#     except:
#         return 0.0


import math

# এই ফাংশনটি আর দরকার নেই যদি আপনি NMEA না পাঠান, তবুও রেখে দিতে পারেন
def sim7600_nmea_to_decimal(raw_value, direction):
    if not raw_value or raw_value == '':
        return 0.0
    try:
        val = float(raw_value)
        degrees = int(val / 100)
        minutes = val - (degrees * 100)
        decimal_val = degrees + (minutes / 60)
        if direction in ['S', 'W']:
            decimal_val = -decimal_val
        return round(decimal_val, 6) 
    except Exception:
        return 0.0

def parse_sim7600_gps(raw_string):
    if not raw_string:
        return None

    try:
        parts = raw_string.split(',')
        
        # ==========================================
        # NEW LOGIC: Handle Clean Decimal Format (Lat,Lng)
        # Device sends: "25.695340,88.658184"
        # ==========================================
        if len(parts) == 2:
            return {
                'latitude': float(parts[0]),
                'longitude': float(parts[1]),
                'speed': 0.0 # স্পিড এখানে নেই, ভিউ থেকে নেওয়া হবে
            }

        # ==========================================
        # OLD LOGIC: Handle Raw NMEA Format
        # ==========================================
        if "SEARCHING" in raw_string or "ERROR" in raw_string:
            return None
            
        if len(parts) < 8:
            return None

        lat_raw = parts[0] 
        lat_dir = parts[1] 
        lon_raw = parts[2] 
        lon_dir = parts[3] 
        
        latitude = sim7600_nmea_to_decimal(lat_raw, lat_dir)
        longitude = sim7600_nmea_to_decimal(lon_raw, lon_dir)
        speed_knots = float(parts[7]) if parts[7] else 0.0
        speed_kmh = speed_knots * 1.852
        
        if latitude == 0.0 or longitude == 0.0:
            return None

        return {
            'latitude': latitude,
            'longitude': longitude,
            'speed': round(speed_kmh, 2)
        }

    except Exception as e:
        print(f"GPS Parsing Error: {e}")
        return None

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  
    try:
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda / 2.0) ** 2

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_meters = R * c
        return round(distance_meters, 2)
    except:
        return 0.0