from django.contrib import admin
from django.utils.html import format_html
from .models import Route, BusStop, Bus, BusLocation,BusSchedule

admin.site.site_header = "University Bus Admin"
admin.site.site_title = "Bus Tracking Portal"
admin.site.index_title = "Welcome to Fleet Management"

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_preview', 'stop_count')
    search_fields = ('name',)

    def color_preview(self, obj):
        return format_html(
            '<span style="background-color: {}; width: 30px; height: 15px; display: inline-block; border: 1px solid #ccc;"></span> <span style="color: #666;">{}</span>',
            obj.color, obj.color
        )
    
    def stop_count(self, obj):
        return obj.stops.count()

@admin.register(BusStop)
class BusStopAdmin(admin.ModelAdmin):
    list_display = ('name', 'route', 'order', 'lat_lng', 'open_map')
    list_filter = ('route',)
    ordering = ('route', 'order')
    list_editable = ('order',)

    def lat_lng(self, obj):
        return f"{obj.latitude:.4f}, {obj.longitude:.4f}"

    def open_map(self, obj):
        url = f"https://www.google.com/maps/search/?api=1&query={obj.latitude},{obj.longitude}"
        return format_html('<a href="{}" target="_blank" style="color:blue;">Map</a>', url)

@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    # 👇 এখানে পরিবর্তন করা হয়েছে: Debugging Fields যোগ করা হয়েছে
    list_display = ('name', 'device_id', 'route', 'is_active', 'current_status', 'last_stop_info')
    list_filter = ('route', 'is_active', 'last_direction')
    search_fields = ('name', 'device_id')

     # এপিআই কি এবং অন্যান্য অটো-ফিল্ড রিড-অনলি করা হয়েছে
    readonly_fields = ('api_key', 'last_stop_order', 'last_direction')

    fieldsets = (
        ('Bus Info', {
            'fields': ('name', 'route', 'is_active')
        }),
        ('Hardware Security (Confidential)', {
            'fields': ('device_id', 'api_key'),
            'description': "ডিভাইস কনফিগার করার সময় এই ID এবং Key ব্যবহার করুন।"
        }),
        ('Live Tracking Data', {
            'fields': ('last_direction', 'last_stop_order', 'trip_status'),
        }),
    )

    def current_status(self, obj):
        color = "green" if obj.is_active else "red"
        return format_html('<span style="color: {};">● {}</span>', color, "Active" if obj.is_active else "Inactive")

    # 👇 বাসের বর্তমান মেমোরি দেখার জন্য কাস্টম কলাম
    def last_stop_info(self, obj):
        return format_html(
            'Dir: <b>{}</b> | Order: <b>{}</b>',
            obj.last_direction,
            obj.last_stop_order
        )
    last_stop_info.short_description = "Live Memory"

@admin.register(BusLocation)
class BusLocationAdmin(admin.ModelAdmin):
    list_display = ('bus', 'timestamp', 'speed', 'direction')
    list_filter = ('bus', 'timestamp')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False


# ----------------------------- Bus schedule Admin ----------------------------- 

@admin.register(BusSchedule)
class BusScheduleAdmin(admin.ModelAdmin):
    list_display = ('trip_name', 'departure_time', 'bus_number', 'direction', 'day_type', 'is_active')
    list_filter = ('day_type', 'direction', 'trip_name') # সাইডবারে ফিল্টার থাকবে
    search_fields = ('bus_number', 'trip_name')
    ordering = ('day_type', 'departure_time')
    
    fieldsets = (
        ('Trip Information', {
            'fields': ('trip_name', 'bus_number', 'note')
        }),
        ('Timing & Route', {
            'fields': ('departure_time', 'direction', 'day_type')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )