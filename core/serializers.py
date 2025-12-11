from rest_framework import serializers
from .models import BusSchedule

class BusScheduleSerializer(serializers.ModelSerializer):
    formatted_time = serializers.SerializerMethodField()
    direction_label = serializers.CharField(source='get_direction_display', read_only=True)

    class Meta:
        model = BusSchedule
        fields = ['id', 'trip_name', 'direction', 'direction_label', 'day_type', 'departure_time', 'formatted_time', 'bus_number', 'note', 'is_active']

    def get_formatted_time(self, obj):
        return obj.departure_time.strftime("%I:%M %p") 