# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter # Router ইম্পোর্ট
from django.views.generic import TemplateView
from .views import LocationUpdateView, get_stops, BusScheduleViewSet

# রাউটার সেটআপ
router = DefaultRouter()
router.register(r'schedule', BusScheduleViewSet, basename='bus_schedule')

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    
    # Bus Tracking APIs
    path('api/update-location/', LocationUpdateView.as_view(), name='update_location'),
    path('api/stops/', get_stops, name='get_stops'),
    path('api/bus/<str:bus_id>/', LocationUpdateView.as_view(), name='get_bus_status'),

    # Schedule API (Router এর মাধ্যমে)
    path('api/', include(router.urls)), 
]