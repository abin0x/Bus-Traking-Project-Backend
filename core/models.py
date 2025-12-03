from django.db import models

class Route(models.Model):
    name = models.CharField(max_length=100) # e.g., "Route 1"
    color = models.CharField(max_length=20, default="blue") # Map Line Color
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Bus(models.Model):
    device_id = models.CharField(max_length=50, unique=True) # Hardware ID (ESP Code)
    name = models.CharField(max_length=50) # Display Name (e.g., "Padma Bus")
    route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True, blank=True)
    api_key = models.CharField(max_length=100, default="secret_key") # Security
    is_active = models.BooleanField(default=True)
    
    # Tracking Fields
    last_stop_order = models.IntegerField(default=0) # শেষ কোন সিরিয়াল স্টপ পার করেছে
    last_direction = models.CharField(max_length=50, default="STOPPED")
    
    # Status Fields
    TRIP_STATUS_CHOICES = [('IDLE', 'Idle'), ('READY', 'Ready'), ('ON_TRIP', 'On Trip')]
    trip_status = models.CharField(max_length=20, choices=TRIP_STATUS_CHOICES, default='IDLE')
    
    # [NEW] বাসটি কখন টার্মিনালে এসে পৌঁছেছে (টাইমার দেখানোর জন্য জরুরি)
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
            models.Index(fields=['bus', '-timestamp']), # কুয়েরি ফাস্ট করার জন্য ইনডেক্সিং
        ]

    def __str__(self):
        return f"{self.bus.name} at {self.timestamp}"
    
class BusStop(models.Model):
    # ১. রিলেশনশিপ: স্টপটি কোন রুটের অংশ?
    route = models.ForeignKey(Route, related_name='stops', on_delete=models.CASCADE)
    
    # ২. স্টপের নাম (যেমন: মিরপুর ১০, কাজীপাড়া)
    name = models.CharField(max_length=100)
    
    # ৩. কোঅর্ডিনেট (ম্যাপে দেখানোর জন্য)
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    # ৪. সিরিয়াল নম্বর (খুব গুরুত্বপূর্ণ)
    order = models.PositiveIntegerField(default=0, help_text="Sequence number (e.g. 1, 2, 3)")

    class Meta:
        ordering = ['order']
        unique_together = ('route', 'order')

    def __str__(self):
        return f"{self.order}. {self.name} ({self.route.name})"