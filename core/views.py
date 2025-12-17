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
# HELPER: GET TRIP INFO
# ==========================================
def get_trip_info(bus_obj, direction_status):
    origin = "Unknown"
    destination = "Unknown"

    if bus_obj.route:
        stops = bus_obj.route.stops.all().order_by('order')
        if stops.exists():
            first_stop_name = stops.first().name
            last_stop_name = stops.last().name

            if direction_status == "UNI_TO_CITY":
                origin = first_stop_name
                destination = last_stop_name
            elif direction_status == "CITY_TO_UNI":
                origin = last_stop_name
                destination = first_stop_name
            else:
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
        """ [FRONTEND API] """
        try:
            active_buses = Bus.objects.filter(is_active=True).select_related('route')
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
                logger.warning("Empty Body received in POST")
                return JsonResponse({'status': 'error', 'message': 'Empty Body'}, status=400)
            
            data = json.loads(body_unicode)

            # 1. Extract Data
            incoming_bus_id = data.get('bus_id')
            raw_gps = data.get('gps_raw', '')
            device_direction = data.get('direction', 'STOPPED')
            incoming_speed = data.get('speed', 0.0)

            # 2. Find Bus
            try:
                bus_obj = Bus.objects.select_related('route').get(device_id=incoming_bus_id)
            except Bus.DoesNotExist:
                logger.error(f"Device not registered: {incoming_bus_id}")
                return JsonResponse({'status': 'error', 'message': 'Device not registered'}, status=404)

            # 3. GPS Parsing
            parsed_data = parse_sim7600_gps(raw_gps)
            if not parsed_data:
                logger.warning(f"Invalid GPS data from {bus_obj.name}: {raw_gps}")
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
            
            # Driver Button Logic
            if device_direction != 'STOPPED' and device_direction != bus_obj.last_direction:
                # ✅ Logged
                logger.info(f"🔘 BUTTON PRESSED: {bus_obj.name} changed {bus_obj.last_direction} -> {device_direction}")
                
                bus_obj.last_direction = device_direction
                if device_direction == "UNI_TO_CITY":
                    bus_obj.last_stop_order = 0
                elif device_direction == "CITY_TO_UNI":
                    bus_obj.last_stop_order = 999 
                
                bus_obj.trip_status = 'READY'
                manual_change_detected = True 

            # Auto Logic
            if bus_obj.route:
                stops = bus_obj.route.stops.all().order_by('order')
                if stops.exists():
                    first_stop = stops.first()
                    last_stop = stops.last()
                    dist_to_start = calculate_distance(lat, lng, first_stop.latitude, first_stop.longitude)
                    dist_to_end = calculate_distance(lat, lng, last_stop.latitude, last_stop.longitude)
                    at_terminal = (dist_to_start <= 100) or (dist_to_end <= 100)

                    # Moving
                    if speed > 5:
                        if bus_obj.trip_status == 'READY':
                            logger.info(f"🚀 {bus_obj.name} started moving. Status: ON_TRIP")
                        
                        bus_obj.trip_status = 'ON_TRIP'
                        if not manual_change_detected:
                            if (100 < dist_to_start < 1000) and bus_obj.last_direction != "UNI_TO_CITY":
                                 logger.info(f"🔄 Auto-Switch: {bus_obj.name} -> UNI_TO_CITY")
                                 bus_obj.last_direction = "UNI_TO_CITY"
                                 bus_obj.last_stop_order = 0
                            elif (100 < dist_to_end < 1000) and bus_obj.last_direction != "CITY_TO_UNI":
                                 logger.info(f"🔄 Auto-Switch: {bus_obj.name} -> CITY_TO_UNI")
                                 bus_obj.last_direction = "CITY_TO_UNI"
                                 bus_obj.last_stop_order = 999
                    
                    # Stopped
                    elif speed < 3 and at_terminal:
                         if bus_obj.trip_status != 'IDLE':
                            bus_obj.trip_status = 'READY'
                            if not manual_change_detected:
                                if (dist_to_start <= 100) and bus_obj.last_direction != "UNI_TO_CITY":
                                    logger.info(f"🤖 Auto-Set: {bus_obj.name} Ready at Start Terminal")
                                    bus_obj.last_direction = "UNI_TO_CITY"
                                    bus_obj.last_stop_order = 0
                                elif (dist_to_end <= 100) and bus_obj.last_direction != "CITY_TO_UNI":
                                    logger.info(f"🤖 Auto-Set: {bus_obj.name} Ready at End Terminal")
                                    bus_obj.last_direction = "CITY_TO_UNI"
                                    bus_obj.last_stop_order = 999

            # ==========================================
            # 📍 5. STOP LOGIC & TRAFFIC
            # ==========================================
            traffic_status = 'normal'
            if speed < 5: traffic_status = 'heavy'
            elif speed < 25: traffic_status = 'medium'

            current_stop_name = None
            is_at_stop = False
            
            if bus_obj.route and bus_obj.last_direction != "STOPPED":
                route_stops = BusStop.objects.filter(route=bus_obj.route)
                for stop in route_stops:
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
                            # ✅ Logged
                            logger.info(f"📍 Progress ({bus_obj.last_direction}): {bus_obj.name} Reached {stop.name}")
                        break 

            # ==========================================
            # 🚀 6. LIVE UPDATE
            # ==========================================
            bus_obj.current_latitude = lat
            bus_obj.current_longitude = lng
            bus_obj.current_speed = speed
            bus_obj.save() 

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
            logger.error("Invalid JSON format received")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format'}, status=400)
        except Exception as e:
            # ✅ Critical Error Logging with Traceback
            logger.exception(f"🔥 Server Error in POST: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ==========================================
# GET STOPS API
# ==========================================
def get_stops(request):
    try:
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
    except Exception as e:
        logger.error(f"Error fetching stops: {e}")
        return JsonResponse({'error': 'Failed to fetch stops'}, status=500)


# ==========================================
# BUS SCHEDULE VIEWS
# ==========================================
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
            if weekday == 4: day_type = 'FRI'
            elif weekday == 5: day_type = 'SAT'
            else: day_type = 'SUN_THU'

            next_slot = BusSchedule.objects.filter(
                day_type=day_type,
                departure_time__gte=current_time,
                is_active=True
            ).order_by('departure_time').first()

            upcoming_buses = []
            next_time_str = ""

            if next_slot:
                target_time = next_slot.departure_time
                upcoming_buses = BusSchedule.objects.filter(
                    day_type=day_type,
                    departure_time=target_time,
                    is_active=True
                )
                next_time_str = target_time.strftime("%I:%M %p")

            serializer = BusScheduleSerializer(upcoming_buses, many=True)
            return Response({
                "status": "success",
                "next_slot": next_time_str,
                "buses": serializer.data
            })
        except Exception as e:
            logger.error(f"Error fetching schedule: {e}")
            return Response({"status": "error", "message": str(e)}, status=500)