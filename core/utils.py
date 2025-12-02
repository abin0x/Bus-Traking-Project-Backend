import math

def sim7600_nmea_to_decimal(raw_value, direction):
    """
    SIM7600 এর 'DDMM.MMMM' ফরম্যাট থেকে 'DD.DDDD' (Decimal Degrees) এ কনভার্ট করে।
    উদাহরণ: "2352.1234" -> 23.8687
    """
    if not raw_value or raw_value == '':
        return 0.0

    try:
        # স্ট্রিং থেকে ফ্লোটে কনভার্ট
        val = float(raw_value)
        
        # ডিগ্রি এবং মিনিট আলাদা করা
        # 2352.1234 কে 100 দিয়ে ভাগ করলে ইন্টিজার অংশ হবে 23 (Degrees)
        degrees = int(val / 100)
        
        # বাকি অংশ হবে মিনিট (52.1234)
        minutes = val - (degrees * 100)
        
        # সূত্র: Degrees + (Minutes / 60)
        decimal_val = degrees + (minutes / 60)
        
        # দক্ষিণ (S) বা পশ্চিম (W) হলে নেগেটিভ হবে
        if direction in ['S', 'W']:
            decimal_val = -decimal_val
            
        return round(decimal_val, 6) # ৬ ঘর পর্যন্ত নির্ভুল
        
    except Exception:
        return 0.0

def parse_sim7600_gps(raw_string):
    """
    ESP32 থেকে আসা 'gps_raw' স্ট্রিংটি পার্স করবে।
    Raw Format Example: 2352.1234,N,09024.5678,E,251025,123456.0,10.0,0.0,0.0
    Index Mapping:
    0: Lat, 1: N/S, 2: Lon, 3: E/W, 4: Date, 5: Time, 6: Alt, 7: Speed
    """
    if not raw_string or "SEARCHING" in raw_string or "ERROR" in raw_string:
        return None

    try:
        parts = raw_string.split(',')
        
        # সঠিক ডেটা হতে হলে কমপক্ষে ৮টি প্যারামিটার থাকতে হবে
        if len(parts) < 8:
            return None

        # ১. ল্যাট-লং কনভার্শন
        lat_raw = parts[0] # e.g., 2352.1234
        lat_dir = parts[1] # e.g., N
        lon_raw = parts[2] # e.g., 09024.5678
        lon_dir = parts[3] # e.g., E
        
        latitude = sim7600_nmea_to_decimal(lat_raw, lat_dir)
        longitude = sim7600_nmea_to_decimal(lon_raw, lon_dir)

        # ২. স্পিড কনভার্শন
        # SIM7600 সাধারণত Knots এ স্পিড দেয়। (1 Knot = 1.852 km/h)
        # যদি ভ্যালু না থাকে তবে ০ ধরা হবে
        speed_knots = float(parts[7]) if parts[7] else 0.0
        speed_kmh = speed_knots * 1.852

        # যদি অক্ষাংশ বা দ্রাঘিমাংশ ০.০ আসে, তার মানে ফিক্স হয়নি
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
    """
    Haversine Formula ব্যবহার করে দুটি জিপিএস পয়েন্টের দূরত্ব (মিটারে) বের করা।
    """
    R = 6371000  # পৃথিবীর ব্যাসার্ধ (মিটারে)

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