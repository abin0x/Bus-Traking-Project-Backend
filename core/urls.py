from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.views.generic import TemplateView
from .views import LocationUpdateView, get_stops, BusScheduleViewSet, NextBusScheduleView
router = DefaultRouter()
router.register(r'schedule', BusScheduleViewSet, basename='bus_schedule')

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('api/', include(router.urls)), 
    path('api/update-location/', LocationUpdateView.as_view(), name='update_location'),
    path('api/stops/', get_stops, name='get_stops'),
    path('api/bus/<str:bus_id>/', LocationUpdateView.as_view(), name='get_bus_status'),
    path('api/next-buses/', NextBusScheduleView.as_view(), name='next_buses'),
    path('auth/', TemplateView.as_view(template_name='auth.html'), name='auth_page'), 
]