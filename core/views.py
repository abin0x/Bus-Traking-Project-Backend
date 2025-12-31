
import json
import logging
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Bus, BusStop, BusSchedule
from .utils import parse_sim7600_gps
from .serializers import BusScheduleSerializer
from .services import BusTrackingService

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class LocationUpdateView(View):
    
    def get(self, request):
        """ [FRONTEND API] """
        try:
            active_buses = Bus.objects.filter(is_active=True).select_related('route').prefetch_related('route__stops')
            bus_list = []
            now = timezone.now()

            for bus in active_buses:
                cached_data = cache.get(f"bus_data_{bus.device_id}")
                
                # পুরনো কোডের সেই timeout লজিক (১০ মিনিট বনাম ২ মিনিট)
                is_on_trip = bus.trip_status == 'ON_TRIP'
                timeout_mins = 10 if is_on_trip else 2
                time_threshold = now - timedelta(minutes=timeout_mins)

                if cached_data:
                    bus_list.append(cached_data)
                elif bus.last_contact and bus.last_contact >= time_threshold:
                    # ক্যাশে না থাকলে ডাটাবেস থেকে রিয়্যালটাইম জেনারেট করা
                    origin, dest = BusTrackingService.get_trip_info(bus, bus.last_direction)
                    bus_list.append({
                        'id': bus.device_id, 'name': bus.name, 'route': bus.route.name if bus.route else "No Route",
                        'lat': bus.current_latitude, 'lng': bus.current_longitude, 'speed': bus.current_speed,
                        'direction_status': bus.last_direction, 'trip_status': bus.trip_status,
                        'origin': origin, 'destination': dest, 'last_seen': bus.last_contact.timestamp()
                    })

            return JsonResponse({'status': 'success', 'buses': bus_list}, status=200)
        except Exception as e:
            logger.error(f"Error in GET: {e}")
            return JsonResponse({'status': 'error', 'message': 'Internal Server Error'}, status=500)

    def post(self, request):
        """ [IOT DEVICE API] """
        try:
            data = json.loads(request.body.decode('utf-8'))
            bus_id = data.get('bus_id')
            api_key = data.get('api_key')
            
            # ১. অথেন্টিকেশন
            bus_obj = Bus.objects.select_related('route').prefetch_related('route__stops').get(device_id=bus_id)
            if bus_obj.api_key != api_key:
                return JsonResponse({'status': 'error', 'message': 'Invalid API Key'}, status=403)

            # ২. জিপিএস ডাটা পার্সিং
            parsed_gps = parse_sim7600_gps(data.get('gps_raw', ''))
            if not parsed_gps:
                return JsonResponse({'status': 'skipped', 'message': 'GPS Fix Waiting'}, status=200)

            # ৩. সার্ভিস লেয়ারকে সমস্ত লজিক কল করা
            BusTrackingService.handle_location_update(
                bus_obj=bus_obj,
                lat=parsed_gps['latitude'],
                lng=parsed_gps['longitude'],
                speed=float(data.get('speed', parsed_gps['speed'])),
                device_direction=data.get('direction', 'STOPPED')
            )

            return JsonResponse({'status': 'success'}, status=200)

        except Bus.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Bus not registered'}, status=404)
        except Exception as e:
            logger.exception(f"Error in POST: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# --- বাকি ভিউগুলো (Schedule/Stops) ---

def get_stops(request):
    try:
        stops = BusStop.objects.select_related('route').all().order_by('route', 'order')
        data = [{"name": s.name, "lat": s.latitude, "lng": s.longitude, "order": s.order, "route": s.route.name} for s in stops]
        return JsonResponse({'stops': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

class BusScheduleViewSet(viewsets.ModelViewSet):
    queryset = BusSchedule.objects.filter(is_active=True).order_by('departure_time')
    serializer_class = BusScheduleSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['day_type', 'direction', 'trip_name']

class NextBusScheduleView(APIView):
    def get(self, request):
        try:
            now = timezone.localtime(timezone.now())
            day_type = 'FRI' if now.weekday() == 4 else 'SAT' if now.weekday() == 5 else 'SUN_THU'
            next_slot = BusSchedule.objects.filter(day_type=day_type, departure_time__gte=now.time(), is_active=True).first()
            
            buses = []
            time_str = ""
            if next_slot:
                buses = BusSchedule.objects.filter(day_type=day_type, departure_time=next_slot.departure_time, is_active=True)
                time_str = next_slot.departure_time.strftime("%I:%M %p")

            serializer = BusScheduleSerializer(buses, many=True)
            return Response({"status": "success", "next_slot": time_str, "buses": serializer.data})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=500)