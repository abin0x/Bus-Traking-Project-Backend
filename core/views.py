# core/views.py
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
from .tasks import process_bus_location_task # টাস্ক ইম্পোর্ট
from .services import BusTrackingService

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class LocationUpdateView(View):
    
    def get(self, request):
        """ [FRONTEND API] - ক্যাশে থেকে লাইভ ডাটা দেখাবে """
        try:
            active_buses = Bus.objects.filter(is_active=True).select_related('route').prefetch_related('route__stops')
            bus_list = []
            now = timezone.now()

            for bus in active_buses:
                cached_data = cache.get(f"bus_data_{bus.device_id}")
                
                is_on_trip = bus.trip_status == 'ON_TRIP'
                time_threshold = now - timedelta(minutes=(10 if is_on_trip else 2))

                if cached_data:
                    bus_list.append(cached_data)
                elif bus.last_contact and bus.last_contact >= time_threshold:
                    origin, dest = BusTrackingService.get_trip_info(bus, bus.last_direction)
                    bus_list.append({
                        'id': bus.device_id, 'name': bus.name, 'lat': bus.current_latitude,
                        'lng': bus.current_longitude, 'speed': bus.current_speed,
                        'direction_status': bus.last_direction, 'origin': origin, 'destination': dest,
                        'last_seen': bus.last_contact.timestamp()
                    })

            return JsonResponse({'status': 'success', 'buses': bus_list}, status=200)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': 'Internal Server Error'}, status=500)

    def post(self, request):
        """ [IOT DEVICE API] - ডাটা পেয়ে সাথে সাথে Celery-তে পাঠাবে """
        try:
            data = json.loads(request.body.decode('utf-8'))
            bus_id = data.get('bus_id')
            api_key = data.get('api_key')
            
            # ১. জিপিএস পার্সিং (ভিউতে করা ভালো যাতে ইনভ্যালিড ডাটা ফিল্টার হয়)
            parsed_gps = parse_sim7600_gps(data.get('gps_raw', ''))
            if not parsed_gps:
                return JsonResponse({'status': 'skipped', 'message': 'No GPS fix'}, status=200)

            # ২. ভারী কাজ Celery-তে হ্যান্ডওভার করা
            # .delay() মেথড কাজটিকে ব্যাকগ্রাউন্ড কিউতে পাঠিয়ে দেয়
            process_bus_location_task.delay(
                bus_id=bus_id,
                lat=parsed_gps['latitude'],
                lng=parsed_gps['longitude'],
                speed=float(data.get('speed', parsed_gps['speed'])),
                direction=data.get('direction', 'STOPPED'),
                api_key=api_key
            )

            # ৩. সাথে সাথে রেসপন্স দেওয়া
            return JsonResponse({'status': 'received'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"POST View Error: {e}")
            return JsonResponse({'status': 'error', 'message': 'Internal Error'}, status=500)

# --- Schedule and Stops Views (Remain same as before) ---
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
            
            buses, time_str = [], ""
            if next_slot:
                buses = BusSchedule.objects.filter(day_type=day_type, departure_time=next_slot.departure_time, is_active=True)
                time_str = next_slot.departure_time.strftime("%I:%M %p")

            serializer = BusScheduleSerializer(buses, many=True)
            return Response({"status": "success", "next_slot": time_str, "buses": serializer.data})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=500)