# core/services.py
import logging
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .utils import calculate_distance
from .models import BusLocation

logger = logging.getLogger(__name__)

class BusTrackingService:
    
    @staticmethod
    def get_trip_info(bus_obj, direction_status):
        """বাসের রুট অনুযায়ী যাত্রা শুরু এবং গন্তব্য নির্ধারণ করা"""
        origin, destination = "Unknown", "Unknown"
        if bus_obj.route:
            stops = list(bus_obj.route.stops.all())
            if stops:
                first_stop_name = stops[0].name
                last_stop_name = stops[-1].name
                if direction_status == "UNI_TO_CITY":
                    origin, destination = first_stop_name, last_stop_name
                else:
                    origin, destination = last_stop_name, first_stop_name
        return origin, destination

    @classmethod
    def handle_location_update(cls, bus_obj, lat, lng, speed, device_direction):
        """ভারী প্রসেসিং লজিক যা এখন ব্যাকগ্রাউন্ডে (Celery) চলবে"""
        
        try:
            update_fields = ['current_latitude', 'current_longitude', 'current_speed', 'last_contact']
            bus_obj.current_latitude = lat
            bus_obj.current_longitude = lng
            bus_obj.current_speed = speed
            
            manual_change_detected = False

            # ১. ডিরেকশন লজিক (বাটন প্রেস)
            if device_direction != 'STOPPED' and device_direction != bus_obj.last_direction:
                bus_obj.last_direction = device_direction
                bus_obj.last_stop_order = 0 if device_direction == "UNI_TO_CITY" else 999
                bus_obj.trip_status = 'READY'
                manual_change_detected = True
                update_fields.extend(['last_direction', 'last_stop_order', 'trip_status'])

            # ২. অটো লজিক (টার্মিনাল ডিটেকশন)
            if bus_obj.route:
                stops = list(bus_obj.route.stops.all())
                if stops:
                    dist_to_start = calculate_distance(lat, lng, stops[0].latitude, stops[0].longitude)
                    dist_to_end = calculate_distance(lat, lng, stops[-1].latitude, stops[-1].longitude)
                    at_terminal = (dist_to_start <= 100) or (dist_to_end <= 100)

                    if speed > 5:
                        if bus_obj.trip_status != 'ON_TRIP':
                            bus_obj.trip_status = 'ON_TRIP'
                            if 'trip_status' not in update_fields: update_fields.append('trip_status')
                        
                        if not manual_change_detected:
                            if (100 < dist_to_start < 1000) and bus_obj.last_direction != "UNI_TO_CITY":
                                bus_obj.last_direction = "UNI_TO_CITY"
                                bus_obj.last_stop_order = 0
                                update_fields.extend(['last_direction', 'last_stop_order'])
                            elif (100 < dist_to_end < 1000) and bus_obj.last_direction != "CITY_TO_UNI":
                                bus_obj.last_direction = "CITY_TO_UNI"
                                bus_obj.last_stop_order = 999
                                update_fields.extend(['last_direction', 'last_stop_order'])
                    
                    elif speed < 3 and at_terminal:
                        if bus_obj.trip_status != 'READY' and bus_obj.trip_status != 'IDLE':
                            bus_obj.trip_status = 'READY'
                            if 'trip_status' not in update_fields: update_fields.append('trip_status')

            # ৩. স্টপ এবং ট্রাফিক ডিটেকশন
            traffic_status = 'heavy' if speed < 5 else 'medium' if speed < 25 else 'normal'
            current_stop_name, is_at_stop = None, False
            
            if bus_obj.route and bus_obj.last_direction != "STOPPED":
                for stop in bus_obj.route.stops.all():
                    if calculate_distance(lat, lng, stop.latitude, stop.longitude) <= 50:
                        current_stop_name, is_at_stop = stop.name, True
                        # প্রোগ্রেস আপডেট
                        if (bus_obj.last_direction == "UNI_TO_CITY" and stop.order > bus_obj.last_stop_order) or \
                           (bus_obj.last_direction == "CITY_TO_UNI" and stop.order < bus_obj.last_stop_order):
                            bus_obj.last_stop_order = stop.order
                            if 'last_stop_order' not in update_fields: update_fields.append('last_stop_order')
                        break

            # ৪. ডাটাবেস সেভ (Transaction Atomic)
            with transaction.atomic():
                bus_obj.save(update_fields=list(set(update_fields)))
                cls._save_history(bus_obj, lat, lng, speed)

            # ৫. ব্রডকাস্ট ডাটা তৈরি
            origin, dest = cls.get_trip_info(bus_obj, bus_obj.last_direction)
            processed_data = {
                'id': bus_obj.device_id, 'name': bus_obj.name, 'route': bus_obj.route.name if bus_obj.route else "No Route",
                'lat': lat, 'lng': lng, 'speed': speed, 'traffic': traffic_status,
                'direction_status': bus_obj.last_direction, 'trip_status': bus_obj.trip_status,
                'current_stop': current_stop_name, 'at_stop': is_at_stop, 'origin': origin, 'destination': dest,
                'last_seen': timezone.now().timestamp()
            }

            # ক্যাশে এবং ওয়েবসকেট ব্রডকাস্ট
            cache.set(f"bus_data_{bus_obj.device_id}", processed_data, timeout=300)
            cls._broadcast_to_socket(processed_data)

            return processed_data

        except Exception as e:
            logger.error(f"Error in Service handle_location_update: {e}")
            raise e

    @staticmethod
    def _save_history(bus_obj, lat, lng, speed):
        """স্মার্ট হিস্টোরি সেভ (১৫ মিটারের বেশি সরলে)"""
        last_loc = BusLocation.objects.filter(bus=bus_obj).order_by('-timestamp').first()
        if not last_loc or calculate_distance(last_loc.latitude, last_loc.longitude, lat, lng) > 15:
            BusLocation.objects.create(bus=bus_obj, latitude=lat, longitude=lng, speed=speed, direction=bus_obj.last_direction)

    @staticmethod
    def _broadcast_to_socket(message):
        """ওয়েবসকেটে ডাটা পাঠানো"""
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)("tracking_group", {"type": "send_update", "message": message})