import json
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db.models import Max, Min
from .models import Bus, BusLocation, BusStop
from .utils import parse_sim7600_gps, calculate_distance

# ==========================================
# HELPER: GET TRIP INFO
# ==========================================
def get_trip_info(bus_obj, direction_status):
    """
    Direction অনুযায়ী Start এবং Destination ডায়নামিকালি সেট করে।
    """
    origin = "Unknown"
    destination = "Unknown"

    if bus_obj.route:
        stops = bus_obj.route.stops.all().order_by('order')
        
        if stops.exists():
            first_stop_name = stops.first().name  # Order 1 (e.g., University)
            last_stop_name = stops.last().name    # Order Max (e.g., City)

            if direction_status == "UNI_TO_CITY":
                origin = first_stop_name
                destination = last_stop_name
            elif direction_status == "CITY_TO_UNI":
                origin = last_stop_name
                destination = first_stop_name
            else:
                # ডিফল্ট: লাস্ট ডিরেকশন অনুযায়ী অথবা সোজা রুট
                if bus_obj.last_direction == "CITY_TO_UNI":
                    origin = last_stop_name
                    destination = first_stop_name
                else:
                    origin = first_stop_name
                    destination = last_stop_name

    return origin, destination


@method_decorator(csrf_exempt, name='dispatch')
class LocationUpdateView(View):
    """
    API Endpoint for Bus Tracking System.
    """

    def get(self, request):
        """
        [FRONTEND API] ম্যাপ লোডের জন্য (Initial State)
        """
        active_buses = Bus.objects.filter(is_active=True).select_related('route')
        bus_list = []

        for bus in active_buses:
            redis_key = f"bus_data_{bus.device_id}"
            cached_data = cache.get(redis_key)

            # মেমোরি থেকে লাস্ট ডিরেকশন বের করা
            current_dir = bus.last_direction if bus.last_direction else "STOPPED"
            origin, dest = get_trip_info(bus, current_dir)

            if cached_data:
                # Redis ডেটা থাকলেও DB থেকে লেটেস্ট স্ট্যাটাস নিচ্ছি
                cached_data['last_order'] = bus.last_stop_order
                cached_data['direction_status'] = current_dir
                cached_data['trip_status'] = bus.trip_status # [NEW] Status added
                cached_data['origin'] = origin
                cached_data['destination'] = dest
                bus_list.append(cached_data)
            else:
                last_loc = BusLocation.objects.filter(bus=bus).order_by('-timestamp').first()
                if last_loc:
                    bus_list.append({
                        'id': bus.device_id,
                        'name': bus.name,
                        'route': bus.route.name if bus.route else "No Route",
                        'lat': last_loc.latitude,
                        'lng': last_loc.longitude,
                        'speed': last_loc.speed,
                        'status': 'offline',
                        'traffic': 'normal',
                        'trip_status': bus.trip_status, # [NEW]
                        'direction_status': current_dir,
                        'last_update': str(last_loc.timestamp),
                        'current_stop': None,
                        'at_stop': False,
                        'last_order': bus.last_stop_order,
                        'origin': origin,
                        'destination': dest
                    })

        return JsonResponse({'status': 'success', 'buses': bus_list}, status=200)

    def post(self, request):
        """
        [IOT DEVICE API] ESP32 থেকে ডেটা রিসিভ
        """
        try:
            body_unicode = request.body.decode('utf-8')
            if not body_unicode:
                return JsonResponse({'status': 'error', 'message': 'Empty Body'}, status=400)
            
            data = json.loads(body_unicode)

            # ১. ডেটা এক্সট্রাকশন
            incoming_bus_id = data.get('bus_id')
            raw_gps = data.get('gps_raw', '')
            # ডিভাইস থেকে আসা ডিরেকশন (বাটন চাপলে ভ্যালু আসবে)
            device_direction = data.get('direction', 'STOPPED')

            # ২. বাস খুঁজে বের করা
            try:
                bus_obj = Bus.objects.select_related('route').get(device_id=incoming_bus_id)
            except Bus.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Device not registered'}, status=404)

            # ==========================================
            # 🔘 1. MANUAL PRIORITY CHECK (DRIVER BUTTON)
            # ==========================================
            manual_change_detected = False
            
            # ড্রাইভার যদি বাটন চাপে (এবং সেটা আগের ডিরেকশন থেকে আলাদা হয়)
            if device_direction != 'STOPPED' and device_direction != bus_obj.last_direction:
                print(f"🔘 Manual Button Pressed: {bus_obj.last_direction} -> {device_direction}")
                
                # ড্রাইভারের ইনপুট সবার আগে সেট হবে
                bus_obj.last_direction = device_direction
                
                if device_direction == "UNI_TO_CITY":
                    bus_obj.last_stop_order = 0
                elif device_direction == "CITY_TO_UNI":
                    bus_obj.last_stop_order = 999 
                
                # ড্রাইভার বাটন চাপলে আমরা ধরে নিচ্ছি ট্রিপ শুরু হচ্ছে
                bus_obj.trip_status = 'ON_TRIP'
                bus_obj.save()
                
                manual_change_detected = True # ফ্ল্যাগ অন করলাম, যাতে অটো লজিক ওভাররাইড না করে

            # ৩. জিপিএস পার্সিং
            parsed_data = parse_sim7600_gps(raw_gps)
            if not parsed_data:
                return JsonResponse({'status': 'skipped', 'message': 'Waiting for GPS fix'}, status=200)

            lat = parsed_data['latitude']
            lng = parsed_data['longitude']
            speed = parsed_data['speed']

            # ==========================================
            # 🧠 2. SMART LOGIC (AUTO DIRECTION / READY / IDLE)
            # ==========================================
            
            if bus_obj.route:
                stops = bus_obj.route.stops.all().order_by('order')
                
                if stops.exists():
                    first_stop = stops.first() # Start (University)
                    last_stop = stops.last()   # End (City)

                    dist_to_start = calculate_distance(lat, lng, first_stop.latitude, first_stop.longitude)
                    dist_to_end = calculate_distance(lat, lng, last_stop.latitude, last_stop.longitude)

                    # --- ZONE A: START TERMINAL (University) ---
                    if dist_to_start <= 100:
                        # Status Check (10-20 min before logic)
                        if speed < 3:
                            bus_obj.trip_status = 'READY'
                        else:
                            bus_obj.trip_status = 'ON_TRIP'
                        
                        # Auto Direction (Only if manual button NOT pressed)
                        if not manual_change_detected:
                            if bus_obj.last_direction != "UNI_TO_CITY":
                                bus_obj.last_direction = "UNI_TO_CITY"
                                bus_obj.last_stop_order = 0
                                print("🔄 Auto-Correction: At Start Terminal")
                        
                        bus_obj.save()

                    # --- ZONE B: END TERMINAL (City) ---
                    elif dist_to_end <= 100:
                        # Status Check (Auto Hide Logic)
                        if speed < 3:
                            bus_obj.trip_status = 'IDLE' # Trip Finished
                            print(f"🏁 Trip Ended (Idle): {bus_obj.name}")
                        else:
                            # যদি এখানেও স্পিড থাকে, তার মানে বাস ঘুরছে বা রেডি হচ্ছে
                            bus_obj.trip_status = 'READY'
                        
                        # Auto Direction (Only if manual button NOT pressed)
                        if not manual_change_detected:
                            if bus_obj.last_direction != "CITY_TO_UNI":
                                bus_obj.last_direction = "CITY_TO_UNI"
                                bus_obj.last_stop_order = 999
                                print("🔄 Auto-Correction: At End Terminal")
                        
                        bus_obj.save()

                    # --- ZONE C: TRANSITION (Leaving Terminal) ---
                    # 100m - 1000m range
                    elif (100 < dist_to_start <= 1000) or (100 < dist_to_end <= 1000):
                        
                        bus_obj.trip_status = 'ON_TRIP'

                        # Auto Direction Switch logic
                        if not manual_change_detected:
                            # If closer to Start -> Going towards City
                            if dist_to_start < dist_to_end:
                                if bus_obj.last_direction != "UNI_TO_CITY":
                                    bus_obj.last_direction = "UNI_TO_CITY"
                                    bus_obj.last_stop_order = 0
                                    print("🔄 Auto-Switch: Leaving Uni -> City")
                            
                            # If closer to End -> Going towards Uni
                            else:
                                if bus_obj.last_direction != "CITY_TO_UNI":
                                    bus_obj.last_direction = "CITY_TO_UNI"
                                    bus_obj.last_stop_order = 999
                                    print("🔄 Auto-Switch: Leaving City -> Uni")
                        
                        bus_obj.save()

                    # --- ZONE D: MIDDLE ROAD ---
                    else:
                        # Ensure status is ON_TRIP
                        if bus_obj.trip_status != 'ON_TRIP':
                            bus_obj.trip_status = 'ON_TRIP'
                            bus_obj.save()
            
            # ==========================================


            # ৪. ট্রাফিক লজিক
            traffic_status = 'normal'
            if speed < 5: traffic_status = 'heavy'
            elif speed < 25: traffic_status = 'medium'

            # ৫. স্টপেজ লজিক (আপডেটেড ডিরেকশন অনুযায়ী)
            current_stop_name = None
            is_at_stop = False
            
            # এখন আমরা নিশ্চিত `bus_obj.last_direction` সঠিক (ম্যানুয়াল বা অটো)
            final_direction = bus_obj.last_direction

            if bus_obj.route and final_direction != "STOPPED":
                route_stops = BusStop.objects.filter(route=bus_obj.route)
                
                for stop in route_stops:
                    dist = calculate_distance(lat, lng, stop.latitude, stop.longitude)
                    
                    if dist <= 50:
                        current_stop_name = stop.name
                        is_at_stop = True
                        should_update = False
                        
                        if final_direction == "UNI_TO_CITY":
                            if stop.order > bus_obj.last_stop_order:
                                should_update = True
                        elif final_direction == "CITY_TO_UNI":
                            if stop.order < bus_obj.last_stop_order:
                                should_update = True
                        
                        if stop.order == bus_obj.last_stop_order:
                             pass

                        if should_update:
                            bus_obj.last_stop_order = stop.order
                            bus_obj.save()
                            print(f"📍 Progress ({final_direction}): Reached {stop.name}")
                        
                        break 

            # ৬. প্যাকেট তৈরি
            origin_name, dest_name = get_trip_info(bus_obj, final_direction)

            processed_data = {
                'id': bus_obj.device_id,
                'name': bus_obj.name,
                'route': bus_obj.route.name if bus_obj.route else "No Route",
                'lat': lat,
                'lng': lng,
                'speed': speed,
                'traffic': traffic_status,
                'direction_status': final_direction,
                'trip_status': bus_obj.trip_status, # 'READY', 'ON_TRIP', 'IDLE'
                'status': 'stopped' if speed < 1 else 'moving',
                
                'current_stop': current_stop_name,
                'at_stop': is_at_stop,
                'last_order': bus_obj.last_stop_order,
                'origin': origin_name,
                'destination': dest_name
            }

            redis_key = f"bus_data_{incoming_bus_id}"
            cache.set(redis_key, processed_data, timeout=300)

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "tracking_group",
                {"type": "send_update", "message": processed_data}
            )

            BusLocation.objects.create(bus=bus_obj, latitude=lat, longitude=lng, speed=speed, direction=final_direction)
            
            return JsonResponse({'status': 'success'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format'}, status=400)
        except Exception as e:
            print(f"Server Error: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ==========================================
# GET STOPS API
# ==========================================
def get_stops(request):
    """
    [API] ম্যাপে দেখানোর জন্য সব স্টপেজের লিস্ট রিটার্ন করে।
    """
    stops = BusStop.objects.select_related('route').all().order_by('route', 'order')
    data = []
    for stop in stops:
        data.append({
            "name": stop.name,
            "lat": stop.latitude,
            "lng": stop.longitude,
            "order": stop.order,
            "route": stop.route.name
        })
    return JsonResponse({'stops': data}, safe=False)

# this is all most okay 