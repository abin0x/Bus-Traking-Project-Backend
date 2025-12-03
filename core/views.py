import json
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Bus, BusLocation, BusStop
from .utils import parse_sim7600_gps, calculate_distance

# ==========================================
# HELPER: GET TRIP INFO (START & END)
# ==========================================
def get_trip_info(bus_obj, direction_status):
    origin = "Unknown"
    destination = "Unknown"
    if bus_obj.route:
        stops = bus_obj.route.stops.all().order_by('order')
        if stops.exists():
            first = stops.first().name
            last = stops.last().name
            if direction_status == "UNI_TO_CITY":
                return first, last
            elif direction_status == "CITY_TO_UNI":
                return last, first
            else:
                # Default based on last memory
                if bus_obj.last_direction == "CITY_TO_UNI":
                    return last, first
                return first, last
    return origin, destination

# ==========================================


@method_decorator(csrf_exempt, name='dispatch')
class LocationUpdateView(View):

    def get(self, request):
        # GET Method - Send data to frontend
        active_buses = Bus.objects.filter(is_active=True).select_related('route')
        bus_list = []
        
        for bus in active_buses:
            redis_key = f"bus_data_{bus.device_id}"
            cached_data = cache.get(redis_key)
            
            # Get fresh data from DB
            current_dir = bus.last_direction
            origin, dest = get_trip_info(bus, current_dir)

            if cached_data:
                # Update cached data with latest DB values
                cached_data['last_order'] = bus.last_stop_order
                cached_data['origin'] = origin
                cached_data['destination'] = dest
                cached_data['direction_status'] = current_dir
                
                # Ensure at_stop exists in cached data
                if 'at_stop' not in cached_data:
                    cached_data['at_stop'] = False
                if 'current_stop' not in cached_data:
                    cached_data['current_stop'] = None
                    
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
                        'direction_status': current_dir,
                        'last_order': bus.last_stop_order,
                        'origin': origin,
                        'destination': dest,
                        'current_stop': None,
                        'at_stop': False
                    })
        
        return JsonResponse({'status': 'success', 'buses': bus_list}, status=200)

    def post(self, request):
        # POST Method - Receive data from IoT device
        try:
            body = request.body.decode('utf-8')
            if not body:
                return JsonResponse({'status': 'error'}, status=400)
                
            data = json.loads(body)

            bus_id = data.get('bus_id')
            raw_gps = data.get('gps_raw', '')
            direction = data.get('direction', 'STOPPED')

            try:
                bus = Bus.objects.select_related('route').get(device_id=bus_id)
            except Bus.DoesNotExist:
                return JsonResponse({'status': 'error', 'msg': 'Device not found'}, status=404)

            # ==========================================
            # DIRECTION CHANGE LOGIC
            # ==========================================
            if direction != 'STOPPED' and bus.last_direction != direction:
                print(f"🔄 Direction Change: {bus.last_direction} -> {direction}")
                
                bus.last_direction = direction
                
                # Reset stop order based on new direction
                if direction == "UNI_TO_CITY":
                    bus.last_stop_order = 0  # Start from first stop
                elif direction == "CITY_TO_UNI":
                    bus.last_stop_order = 999  # Start from last stop
                
                bus.save()  # Save immediately to DB

            # GPS Parse
            gps_data = parse_sim7600_gps(raw_gps)
            if not gps_data:
                return JsonResponse({'status': 'skipped'}, status=200)
            
            lat, lng, speed = gps_data['latitude'], gps_data['longitude'], gps_data['speed']
            
            # Traffic calculation
            traffic = 'normal'
            if speed < 5:
                traffic = 'heavy'
            elif speed < 25:
                traffic = 'medium'

            # ==========================================
            # 🛑 CORRECT STOPPAGE LOGIC (Fixed Version)
            # ==========================================
            current_stop_name = None
            is_at_stop = False
            detected_order = bus.last_stop_order  # Default to current order

            if bus.route and direction != "STOPPED":
                # Get all stops for this route
                stops = BusStop.objects.filter(route=bus.route).order_by('order')
                
                for stop in stops:
                    dist = calculate_distance(lat, lng, stop.latitude, stop.longitude)
                    
                    # Check if within 50 meters of stop
                    if dist <= 50:
                        current_stop_name = stop.name
                        is_at_stop = True
                        detected_order = stop.order
                        
                        print(f"📍 Near Stop: {stop.name} (Order: {stop.order}, Dist: {dist:.1f}m)")
                        
                        # Check if bus has progressed to this stop
                        should_update = False
                        
                        if direction == "UNI_TO_CITY":
                            # Forward direction: stop.order should be greater than last_stop_order
                            if stop.order > bus.last_stop_order:
                                should_update = True
                                print(f"   ✅ Progress: {bus.last_stop_order} -> {stop.order} (Forward)")
                                
                        elif direction == "CITY_TO_UNI":
                            # Reverse direction: stop.order should be less than last_stop_order
                            if stop.order < bus.last_stop_order:
                                should_update = True
                                print(f"   ✅ Progress: {bus.last_stop_order} -> {stop.order} (Reverse)")
                        
                        # If bus is at the same stop (stopped at station), update to confirm
                        elif stop.order == bus.last_stop_order:
                            should_update = True
                            print(f"   🔄 At same stop: {stop.order} (Confirming)")
                        
                        # Update if needed
                        if should_update:
                            bus.last_stop_order = stop.order
                            bus.save()
                            print(f"   📝 Updated last_stop_order to: {stop.order}")
                        
                        break  # Found nearest stop, exit loop
            
            # If not at any stop, check if we're moving away from last stop
            elif bus.route and speed > 10:
                # If moving fast and not at a stop, we're between stops
                is_at_stop = False
                current_stop_name = None
                print(f"🚌 Moving between stops at {speed} km/h")

            # ==========================================

            # Get origin and destination info
            origin, dest = get_trip_info(bus, direction)

            # Prepare payload for WebSocket and cache
            payload = {
                'id': bus.device_id,
                'name': bus.name,
                'route': bus.route.name if bus.route else "No Route",
                'lat': lat,
                'lng': lng,
                'speed': speed,
                'traffic': traffic,
                'direction_status': direction,
                'status': 'moving' if speed > 1 else 'stopped',
                'current_stop': current_stop_name,
                'at_stop': is_at_stop,
                'last_order': bus.last_stop_order,  # Always use bus.last_stop_order (DB value)
                'origin': origin,
                'destination': dest
            }

            # Cache the payload
            cache.set(f"bus_data_{bus_id}", payload, timeout=300)

            # Send update via WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "tracking_group",
                {"type": "send_update", "message": payload}
            )

            # Save to location history
            BusLocation.objects.create(
                bus=bus,
                latitude=lat,
                longitude=lng,
                speed=speed,
                direction=direction
            )

            # Return success response
            return JsonResponse({
                'status': 'success',
                'at_stop': is_at_stop,
                'stop_name': current_stop_name,
                'last_order': bus.last_stop_order
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'msg': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f"❌ Error in LocationUpdateView: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)


# ==========================================
# GET STOPS API
# ==========================================
def get_stops(request):
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


# ==========================================
# GET SINGLE BUS STATUS (Optional - for debugging)
# ==========================================
def get_bus_status(request, bus_id):
    try:
        bus = Bus.objects.get(device_id=bus_id)
        redis_key = f"bus_data_{bus_id}"
        cached_data = cache.get(redis_key)
        
        if cached_data:
            return JsonResponse({'status': 'success', 'bus': cached_data})
        else:
            return JsonResponse({
                'status': 'success',
                'bus': {
                    'id': bus.device_id,
                    'name': bus.name,
                    'last_direction': bus.last_direction,
                    'last_stop_order': bus.last_stop_order,
                    'route': bus.route.name if bus.route else None
                }
            })
    except Bus.DoesNotExist:
        return JsonResponse({'status': 'error', 'msg': 'Bus not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)


# ==========================================
# RESET BUS STATUS (Optional - for testing)
# ==========================================
@csrf_exempt
def reset_bus(request, bus_id):
    if request.method == 'POST':
        try:
            bus = Bus.objects.get(device_id=bus_id)
            bus.last_direction = "UNI_TO_CITY"
            bus.last_stop_order = 0
            bus.save()
            
            # Clear cache
            cache.delete(f"bus_data_{bus_id}")
            
            return JsonResponse({
                'status': 'success',
                'message': f'Bus {bus_id} reset to initial state'
            })
        except Bus.DoesNotExist:
            return JsonResponse({'status': 'error', 'msg': 'Bus not found'}, status=404)
    return JsonResponse({'status': 'error', 'msg': 'Invalid method'}, status=400)