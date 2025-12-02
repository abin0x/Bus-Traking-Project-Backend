import json
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Bus, BusLocation
from .utils import parse_sim7600_gps

@method_decorator(csrf_exempt, name='dispatch')
class LocationUpdateView(View):
    """
    API Endpoint for Bus Tracking System.
    """

    def get(self, request):
        """
        [FRONTEND API]
        ম্যাপ লোড হওয়ার সময় সব অ্যাক্টিভ বাসের ডেটা রিটার্ন করে।
        """
        active_buses = Bus.objects.filter(is_active=True).select_related('route')
        bus_list = []

        for bus in active_buses:
            # Redis থেকে ডেটা চেক
            redis_key = f"bus_data_{bus.device_id}"
            cached_data = cache.get(redis_key)

            if cached_data:
                bus_list.append(cached_data)
            else:
                # Redis-এ না থাকলে DB থেকে লাস্ট ডেটা
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
                        'direction_status': last_loc.direction,
                        'last_update': str(last_loc.timestamp)
                    })

        return JsonResponse({'status': 'success', 'buses': bus_list}, status=200)

    def post(self, request):
        """
        [IOT DEVICE API]
        ESP32 (SIM7600) থেকে ডেটা রিসিভ করার লজিক।
        """
        try:
            body_unicode = request.body.decode('utf-8')
            if not body_unicode:
                return JsonResponse({'status': 'error', 'message': 'Empty Body'}, status=400)
            
            data = json.loads(body_unicode)

            # ১. আপনার ESP32 কোড অনুযায়ী ফিল্ডগুলো নেওয়া
            # ESP32 Code sends: "bus_id", "gps_raw", "direction", "type"
            incoming_bus_id = data.get('bus_id')    # "BUS-01"
            raw_gps = data.get('gps_raw', '')       # "2352.1234,N,..."
            direction_status = data.get('direction', 'STOPPED') 

            # ২. ডিভাইস ম্যাপিং (সবচেয়ে গুরুত্বপূর্ণ)
            # ডাটাবেসে চেক করছি "BUS-01" নামে কোনো ডিভাইস আছে কিনা
            try:
                bus_obj = Bus.objects.select_related('route').get(device_id=incoming_bus_id)
            except Bus.DoesNotExist:
                print(f"⚠️ Access Denied: Unknown Device ID '{incoming_bus_id}'")
                # 403 এর বদলে 404 দিচ্ছি যাতে লগে ক্লিয়ার থাকে
                return JsonResponse({'status': 'error', 'message': 'Device not registered'}, status=404)

            # NOTE: API Key চেক রিমুভ করা হয়েছে কারণ আপনার বর্তমান ESP32 কোডে API Key পাঠানো হচ্ছে না।

            # ৩. জিপিএস পার্সিং (SIM7600 লজিক)
            parsed_data = parse_sim7600_gps(raw_gps)
            
            if not parsed_data:
                # জিপিএস ফিক্স না হলে "skipped" রিটার্ন করছি
                # print(f"⏳ GPS Searching for {incoming_bus_id}...") 
                return JsonResponse({'status': 'skipped', 'message': 'Waiting for GPS fix'}, status=200)

            lat = parsed_data['latitude']
            lng = parsed_data['longitude']
            speed = parsed_data['speed']

            # ৪. ট্রাফিক স্ট্যাটাস লজিক
            traffic_status = 'normal'
            if speed < 5:
                traffic_status = 'heavy'   # জ্যাম
            elif speed < 25:
                traffic_status = 'medium'  # স্লো

            # ৫. ফ্রন্টএন্ড প্যাকেট তৈরি (Name Mapping সহ)
            processed_data = {
                'id': bus_obj.device_id,
                'name': bus_obj.name,          # DB থেকে সুন্দর নাম (Padma Express)
                'route': bus_obj.route.name if bus_obj.route else "No Route",
                'lat': lat,
                'lng': lng,
                'speed': speed,
                'traffic': traffic_status,
                'direction_status': direction_status,
                'status': 'moving' if speed > 1 else 'stopped'
            }

            # ৬. Redis Cache আপডেট (৫ মিনিটের জন্য)
            redis_key = f"bus_data_{incoming_bus_id}"
            cache.set(redis_key, processed_data, timeout=300)

            # ৭. WebSocket Broadcast (রিয়েল-টাইম)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "tracking_group",
                {
                    "type": "send_update",
                    "message": processed_data
                }
            )

            # ৮. ডাটাবেসে হিস্ট্রি সেভ
            BusLocation.objects.create(
                bus=bus_obj,
                latitude=lat,
                longitude=lng,
                speed=speed,
                direction=direction_status
            )

            print(f"✅ Update: {bus_obj.name} | Speed: {speed} km/h | Dir: {direction_status}")
            return JsonResponse({'status': 'success'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format'}, status=400)
        except Exception as e:
            print(f"❌ Server Error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Internal Server Error'}, status=500)