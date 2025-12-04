from rest_framework import serializers
from .models import BusSchedule

class BusScheduleSerializer(serializers.ModelSerializer):
    # ফ্রন্টএন্ডে দেখানোর জন্য হিউম্যান রিডেবল টাইম ফরম্যাট
    formatted_time = serializers.SerializerMethodField()
    direction_label = serializers.CharField(source='get_direction_display', read_only=True)

    class Meta:
        model = BusSchedule
        fields = ['id', 'trip_name', 'direction', 'direction_label', 'day_type', 'departure_time', 'formatted_time', 'bus_number', 'note', 'is_active']

    def get_formatted_time(self, obj):
        return obj.departure_time.strftime("%I:%M %p") # 08:30 AM ফরম্যাটে দেখাবে