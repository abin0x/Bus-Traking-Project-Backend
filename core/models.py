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

    def __str__(self):
        return f"{self.name} ({self.device_id})"

class BusLocation(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    speed = models.FloatField(default=0.0)
    direction = models.CharField(max_length=20, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

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
    # বাস কোনটার পর কোনটায় যাবে তা বোঝানোর জন্য (1, 2, 3...)
    order = models.PositiveIntegerField(default=0, help_text="Sequence number (e.g. 1, 2, 3)")

    class Meta:
        ordering = ['order'] # ডাটাবেস থেকে আনার সময় অটোমেটিক সিরিয়াল অনুযায়ী আসবে
        unique_together = ('route', 'order') # একই রুটে একই সিরিয়াল নম্বরের দুটি স্টপ হতে পারবে না

    def __str__(self):
        return f"{self.order}. {self.name} ({self.route.name})"