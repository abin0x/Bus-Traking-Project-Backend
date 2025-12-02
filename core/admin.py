from django.contrib import admin
from django.utils.html import format_html
from .models import Route, BusStop, Bus, BusLocation

admin.site.site_header = "University Bus Admin"
admin.site.site_title = "Bus Tracking Portal"
admin.site.index_title = "Welcome to Fleet Management"

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_preview', 'stop_count', 'description')
    search_fields = ('name',)

    def color_preview(self, obj):
        return format_html(
            '<span style="background-color: {}; width: 30px; height: 15px; display: inline-block; border: 1px solid #ccc;"></span> <span style="color: #666;">{}</span>',
            obj.color, obj.color
        )
    color_preview.short_description = 'Route Color'

    def stop_count(self, obj):
        # FIX: models.py তে related_name='stops' থাকায় এখানে 'stops' ব্যবহার করতে হবে
        return obj.stops.count() 
    stop_count.short_description = 'Total Stops'


@admin.register(BusStop)
class BusStopAdmin(admin.ModelAdmin):
    list_display = ('name', 'route', 'order', 'lat_lng_display', 'open_map')
    list_filter = ('route',)
    search_fields = ('name',)
    ordering = ('route', 'order')
    list_editable = ('order',)

    def lat_lng_display(self, obj):
        return f"{obj.latitude:.4f}, {obj.longitude:.4f}"
    lat_lng_display.short_description = "Coords"

    def open_map(self, obj):
        url = f"https://www.google.com/maps/search/?api=1&query={obj.latitude},{obj.longitude}"
        return format_html('<a href="{}" target="_blank" style="background: #4CAF50; color: white; padding: 3px 8px; border-radius: 4px; text-decoration: none;">View Map</a>', url)
    open_map.short_description = "Map Check"


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('name', 'device_id', 'route', 'is_active', 'status_badge')
    list_filter = ('route', 'is_active')
    search_fields = ('name', 'device_id')
    list_editable = ('route', 'is_active')
    
    fieldsets = (
        ('Display Info', {
            'fields': ('name', 'route', 'is_active')
        }),
        ('Hardware Config', {
            'fields': ('device_id', 'api_key'),
            'description': 'These fields link to the physical ESP32 device.'
        }),
    )

    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✔ Active</span>')
        return format_html('<span style="color: red; font-weight: bold;">✖ Inactive</span>')
    status_badge.short_description = "Status"


@admin.register(BusLocation)
class BusLocationAdmin(admin.ModelAdmin):
    list_display = ('bus', 'timestamp', 'speed', 'direction', 'open_map_link')
    list_filter = ('bus', 'timestamp')
    date_hierarchy = 'timestamp'
    list_per_page = 50

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False

    def open_map_link(self, obj):
        if obj.latitude and obj.longitude:
            url = f"https://www.google.com/maps/search/?api=1&query={obj.latitude},{obj.longitude}"
            return format_html('<a href="{}" target="_blank" style="color: blue;">Open in Maps</a>', url)
        return "-"
    open_map_link.short_description = "Location Check"