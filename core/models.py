from django.db import models

class Route(models.Model):
    name = models.CharField(max_length=100) 
    color = models.CharField(max_length=20, default="blue") 
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Bus(models.Model):
    device_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=50) 
    route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True, blank=True)
    api_key = models.CharField(max_length=100, default="secret_key") 
    is_active = models.BooleanField(default=True)
    last_stop_order = models.IntegerField(default=0) 
    last_direction = models.CharField(max_length=50, default="STOPPED")
    TRIP_STATUS_CHOICES = [('IDLE', 'Idle'), ('READY', 'Ready'), ('ON_TRIP', 'On Trip')]
    trip_status = models.CharField(max_length=20, choices=TRIP_STATUS_CHOICES, default='IDLE')
    last_arrival_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.device_id})"

class BusLocation(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    speed = models.FloatField(default=0.0)
    direction = models.CharField(max_length=20, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['bus', '-timestamp']), 
        ]

    def __str__(self):
        return f"{self.bus.name} at {self.timestamp}"
    
class BusStop(models.Model):
    route = models.ForeignKey(Route, related_name='stops', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    order = models.PositiveIntegerField(default=0, help_text="Sequence number (e.g. 1, 2, 3)")
    class Meta:
        ordering = ['order']
        unique_together = ('route', 'order')

    def __str__(self):
        return f"{self.order}. {self.name} ({self.route.name})"

# ---------------Bus Schedule Model Added Below--------------- 
class BusSchedule(models.Model):
    DIRECTION_CHOICES = [
        ('CAMPUS_TO_CITY', 'Campus to City'),
        ('CAMPUS_TO_BRTCDEPOT', 'Campus to BRTC Depot'),
        ('CAMPUS_TO_DOSHMILE', 'Campus to Doshmile'),
        ('CITY_TO_CAMPUS', 'City to Campus'),
    ]
    DAY_TYPE_CHOICES = [
        ('SUN_THU', 'Sunday to Thursday (Regular)'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
        ('TUE', 'Tuesday (Special)'),
    ]

    trip_name = models.CharField(max_length=100) 
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES)
    day_type = models.CharField(max_length=10, choices=DAY_TYPE_CHOICES, default='SUN_THU')
    
    departure_time = models.TimeField() 
    bus_number = models.CharField(max_length=100) 
    note = models.CharField(max_length=200, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['departure_time'] 
    def __str__(self):
        return f"{self.trip_name} - {self.departure_time} ({self.get_direction_display()})"