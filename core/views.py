import json
import logging
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db.models import Max, Min
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets

from .models import Bus, BusLocation, BusStop, BusSchedule
from .utils import parse_sim7600_gps, calculate_distance
from .serializers import BusScheduleSerializer

# ✅ Setup Logger
logger = logging.getLogger(__name__)

# ==========================================
# HELPER: GET TRIP INFO (Optimized)
# ==========================================
def get_trip_info(bus_obj, direction_status):
    origin = "Unknown"
    destination = "Unknown"

    if bus_obj.route:
        # 🚀 OPTIMIZATION: stops.all() এখন DB হিট করবে না (prefetch এর কারণে)
        # আমরা list() কনভার্ট করছি যাতে মেমোরি থেকে ডাটা আসে
        stops = list(bus_obj.route.stops.all())
        
        if stops:
            first_stop_name = stops[0].name
            last_stop_name = stops[-1].name

            if direction_status == "UNI_TO_CITY":
                origin = first_stop_name
                destination = last_stop_name
            elif direction_status == "CITY_TO_UNI":
                origin = last_stop_name
                destination = first_stop_name
            else:
                # Default Logic based on last direction
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
    Highly Optimized for Production.
    """

    def get(self, request):
        """ [FRONTEND API] """
        try:
            # 🚀 OPTIMIZATION: prefetch_related যোগ করা হয়েছে (N+1 Problem Fix)
            active_buses = Bus.objects.filter(is_active=True)\
                .select_related('route')\
                .prefetch_related('route__stops') 
            
            bus_list = []
            now = timezone.now()

            for bus in active_buses:
                redis_key = f"bus_data_{bus.device_id}"
                cached_data = cache.get(redis_key)

                is_on_trip = bus.trip_status == 'ON_TRIP'
                timeout_minutes = 10 if is_on_trip else 2
                time_threshold = now - timedelta(minutes=timeout_minutes)

                should_include = False
                last_update_ts = None 
                lat, lng, speed = None, None, 0.0

                if cached_data:
                    should_include = True
                    last_update_ts = cached_data.get('last_seen', now.timestamp())
                # Live Field Check
                elif bus.last_contact and bus.last_contact >= time_threshold:
                    if bus.current_latitude and bus.current_longitude:
                        should_include = True
                        last_update_ts = bus.last_contact.timestamp()
                        lat = bus.current_latitude
                        lng = bus.current_longitude
                        speed = bus.current_speed

                if should_include:
                    current_dir = bus.last_direction if bus.last_direction else "STOPPED"
                    origin, dest = get_trip_info(bus, current_dir)
                    next_departure_text = "Departs in few min" if bus.trip_status == 'READY' else ""

                    if cached_data:
                        cached_data['last_order'] = bus.last_stop_order
                        cached_data['direction_status'] = current_dir
                        cached_data['trip_status'] = bus.trip_status
                        cached_data['next_departure'] = next_departure_text
                        cached_data['origin'] = origin
                        cached_data['destination'] = dest
                        bus_list.append(cached_data)
                    else:
                        bus_list.append({
                            'id': bus.device_id,
                            'name': bus.name,
                            'route': bus.route.name if bus.route else "No Route",
                            'lat': lat, 'lng': lng, 'speed': speed,
                            'status': 'offline', 'traffic': 'normal',
                            'trip_status': bus.trip_status,
                            'next_departure': next_departure_text,
                            'direction_status': current_dir,
                            'last_update': str(bus.last_contact),
                            'last_seen': last_update_ts,
                            'current_stop': None, 'at_stop': False,
                            'last_order': bus.last_stop_order,
                            'origin': origin, 'destination': dest
                        })

            return JsonResponse({'status': 'success', 'buses': bus_list}, status=200)
        except Exception as e:
            logger.error(f"Error in GET request: {e}")
            return JsonResponse({'status': 'error', 'message': 'Server Error'}, status=500)

    def post(self, request):
        """ [IOT DEVICE API] """
        try:
            body_unicode = request.body.decode('utf-8')
            if not body_unicode:
                return JsonResponse({'status': 'error', 'message': 'Empty Body'}, status=400)
            
            data = json.loads(body_unicode)

            incoming_bus_id = data.get('bus_id')
            raw_gps = data.get('gps_raw', '')
            device_direction = data.get('direction', 'STOPPED')
            incoming_speed = data.get('speed', 0.0)

            try:
                # 🚀 OPTIMIZATION: stops গুলোও prefetch করে নিচ্ছি লজিকের জন্য
                bus_obj = Bus.objects.select_related('route')\
                    .prefetch_related('route__stops')\
                    .get(device_id=incoming_bus_id)
            except Bus.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Device not registered'}, status=404)

            parsed_data = parse_sim7600_gps(raw_gps)
            if not parsed_data:
                return JsonResponse({'status': 'skipped', 'message': 'Waiting for GPS fix'}, status=200)

            lat = parsed_data['latitude']
            lng = parsed_data['longitude']
            try:
                speed = float(incoming_speed)
            except:
                speed = parsed_data['speed']

            # ==========================================
            # 🔘 4. LOGIC: MANUAL & AUTO DIRECTION
            # ==========================================
            manual_change_detected = False
            
            # Fields that might change during logic
            update_fields_list = ['current_latitude', 'current_longitude', 'current_speed', 'last_contact']
            
            if device_direction != 'STOPPED' and device_direction != bus_obj.last_direction:
                logger.info(f"🔘 BUTTON PRESSED: {bus_obj.name} changed {bus_obj.last_direction} -> {device_direction}")
                
                bus_obj.last_direction = device_direction
                if device_direction == "UNI_TO_CITY":
                    bus_obj.last_stop_order = 0
                elif device_direction == "CITY_TO_UNI":
                    bus_obj.last_stop_order = 999 
                
                bus_obj.trip_status = 'READY'
                manual_change_detected = True
                
                # লজিক চেঞ্জ হলে এগুলোও আপডেট করতে হবে
                update_fields_list.extend(['last_direction', 'last_stop_order', 'trip_status'])

            # Auto Logic
            if bus_obj.route:
                # prefetch করায় এখানে আর DB হিট হবে না
                stops = list(bus_obj.route.stops.all()) 
                
                if stops:
                    first_stop = stops[0]
                    last_stop = stops[-1]
                    dist_to_start = calculate_distance(lat, lng, first_stop.latitude, first_stop.longitude)
                    dist_to_end = calculate_distance(lat, lng, last_stop.latitude, last_stop.longitude)
                    at_terminal = (dist_to_start <= 100) or (dist_to_end <= 100)

                    # Moving
                    if speed > 5:
                        if bus_obj.trip_status == 'READY':
                             logger.info(f"🚀 {bus_obj.name} started moving. Status: ON_TRIP")
                        
                        if bus_obj.trip_status != 'ON_TRIP':
                             bus_obj.trip_status = 'ON_TRIP'
                             if 'trip_status' not in update_fields_list: update_fields_list.append('trip_status')

                        if not manual_change_detected:
                            if (100 < dist_to_start < 1000) and bus_obj.last_direction != "UNI_TO_CITY":
                                 bus_obj.last_direction = "UNI_TO_CITY"
                                 bus_obj.last_stop_order = 0
                                 update_fields_list.extend(['last_direction', 'last_stop_order'])
                            elif (100 < dist_to_end < 1000) and bus_obj.last_direction != "CITY_TO_UNI":
                                 bus_obj.last_direction = "CITY_TO_UNI"
                                 bus_obj.last_stop_order = 999
                                 update_fields_list.extend(['last_direction', 'last_stop_order'])
                    
                    # Stopped
                    elif speed < 3 and at_terminal:
                         if bus_obj.trip_status != 'IDLE':
                            if bus_obj.trip_status != 'READY':
                                bus_obj.trip_status = 'READY'
                                if 'trip_status' not in update_fields_list: update_fields_list.append('trip_status')

                            if not manual_change_detected:
                                if (dist_to_start <= 100) and bus_obj.last_direction != "UNI_TO_CITY":
                                    bus_obj.last_direction = "UNI_TO_CITY"
                                    bus_obj.last_stop_order = 0
                                    update_fields_list.extend(['last_direction', 'last_stop_order'])
                                elif (dist_to_end <= 100) and bus_obj.last_direction != "CITY_TO_UNI":
                                    bus_obj.last_direction = "CITY_TO_UNI"
                                    bus_obj.last_stop_order = 999
                                    update_fields_list.extend(['last_direction', 'last_stop_order'])

            # ==========================================
            # 📍 5. STOP LOGIC & TRAFFIC
            # ==========================================
            traffic_status = 'normal'
            if speed < 5: traffic_status = 'heavy'
            elif speed < 25: traffic_status = 'medium'

            current_stop_name = None
            is_at_stop = False
            
            if bus_obj.route and bus_obj.last_direction != "STOPPED":
                # এখানেও prefetch করা list ব্যবহার করব
                stops = list(bus_obj.route.stops.all())
                for stop in stops:
                    if calculate_distance(lat, lng, stop.latitude, stop.longitude) <= 50:
                        current_stop_name = stop.name
                        is_at_stop = True
                        
                        should_update = False
                        if bus_obj.last_direction == "UNI_TO_CITY" and stop.order > bus_obj.last_stop_order:
                             should_update = True
                        elif bus_obj.last_direction == "CITY_TO_UNI" and stop.order < bus_obj.last_stop_order:
                             should_update = True
                        
                        if should_update:
                            bus_obj.last_stop_order = stop.order
                            if 'last_stop_order' not in update_fields_list: update_fields_list.append('last_stop_order')
                            logger.info(f"📍 Progress: {bus_obj.name} Reached {stop.name}")
                        break 

            # ==========================================
            # 🚀 6. LIVE UPDATE (Optimized Save)
            # ==========================================
            bus_obj.current_latitude = lat
            bus_obj.current_longitude = lng
            bus_obj.current_speed = speed
            
            # 🚀 OPTIMIZATION: শুধু প্রয়োজনীয় ফিল্ড আপডেট করা
            # list(set(...)) ডুপ্লিকেট ফিল্ড রিমুভ করার জন্য
            bus_obj.save(update_fields=list(set(update_fields_list)))

            # ==========================================
            # 📡 7. BROADCAST (REDIS)
            # ==========================================
            origin_name, dest_name = get_trip_info(bus_obj, bus_obj.last_direction)
            next_departure_text = "Departs in few min" if bus_obj.trip_status == 'READY' else ""

            processed_data = {
                'id': bus_obj.device_id,
                'name': bus_obj.name,
                'route': bus_obj.route.name if bus_obj.route else "No Route",
                'lat': lat, 'lng': lng, 'speed': speed,
                'traffic': traffic_status,
                'direction_status': bus_obj.last_direction,
                'trip_status': bus_obj.trip_status, 
                'next_departure': next_departure_text, 
                'status': 'stopped' if speed < 1 else 'moving',
                'current_stop': current_stop_name,
                'at_stop': is_at_stop,
                'last_order': bus_obj.last_stop_order,
                'origin': origin_name,
                'destination': dest_name,
                'last_seen': timezone.now().timestamp() 
            }

            redis_key = f"bus_data_{incoming_bus_id}"
            cache.set(redis_key, processed_data, timeout=300)

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "tracking_group",
                {"type": "send_update", "message": processed_data}
            )

            # ==========================================
            # 💾 8. SMART HISTORY SAVE
            # ==========================================
            should_save_history = True
            last_location = BusLocation.objects.filter(bus=bus_obj).order_by('-timestamp').first()
            
            if last_location:
                distance_moved = calculate_distance(
                    last_location.latitude, last_location.longitude,
                    lat, lng
                )
                if distance_moved < 15:  
                    should_save_history = False
            
            if should_save_history:
                BusLocation.objects.create(
                    bus=bus_obj, latitude=lat, longitude=lng, 
                    speed=speed, direction=bus_obj.last_direction
                )
            
            return JsonResponse({'status': 'success'}, status=200)

        except json.JSONDecodeError:
            logger.error("Invalid JSON format")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format'}, status=400)
        except Exception as e:
            logger.exception(f"🔥 Server Error in POST: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# Stops API and Schedule Views remain same...
def get_stops(request):
    try:
        stops = BusStop.objects.select_related('route').all().order_by('route', 'order')
        data = [{"name": s.name, "lat": s.latitude, "lng": s.longitude, "order": s.order, "route": s.route.name} for s in stops]
        return JsonResponse({'stops': data}, safe=False)
    except Exception as e:
        logger.error(f"Error fetching stops: {e}")
        return JsonResponse({'error': 'Failed'}, status=500)

class BusScheduleViewSet(viewsets.ModelViewSet):
    queryset = BusSchedule.objects.filter(is_active=True).order_by('departure_time')
    serializer_class = BusScheduleSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['day_type', 'direction', 'trip_name']

class NextBusScheduleView(APIView):
    def get(self, request):
        try:
            now = timezone.localtime(timezone.now())
            current_time = now.time()
            weekday = now.weekday()
            day_type = 'FRI' if weekday == 4 else 'SAT' if weekday == 5 else 'SUN_THU'

            next_slot = BusSchedule.objects.filter(
                day_type=day_type, departure_time__gte=current_time, is_active=True
            ).order_by('departure_time').first()

            upcoming_buses = []
            next_time_str = ""
            if next_slot:
                target_time = next_slot.departure_time
                upcoming_buses = BusSchedule.objects.filter(
                    day_type=day_type, departure_time=target_time, is_active=True
                )
                next_time_str = target_time.strftime("%I:%M %p")

            serializer = BusScheduleSerializer(upcoming_buses, many=True)
            return Response({"status": "success", "next_slot": next_time_str, "buses": serializer.data})
        except Exception as e:
            logger.error(f"Error fetching schedule: {e}")
            return Response({"status": "error", "message": str(e)}, status=500)