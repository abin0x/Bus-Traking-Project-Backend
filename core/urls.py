# core/urls.py

from django.urls import path
from django.views.generic import TemplateView
from .views import LocationUpdateView,get_stops

urlpatterns = [
    
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('api/update-location/', LocationUpdateView.as_view(), name='update_location'),
    # path('api/stops/<str:route_name>/', get_stops, name='get_stops'),
    path('api/stops/', get_stops, name='get_stops'),
]


# from django.urls import path
# from django.views.generic import TemplateView
# from . import views

# urlpatterns = [
#     path('', TemplateView.as_view(template_name='index.html'), name='home'),
#     path('api/update-location/', views.LocationUpdateView.as_view(), name='update_location'),
#     path('api/location/', views.LocationUpdateView.as_view(), name='get_location'),
#     path('api/stops/', views.get_stops, name='get_stops'),
#     path('api/bus/<str:bus_id>/', views.get_bus_status, name='get_bus_status'),
#     path('api/reset/<str:bus_id>/', views.reset_bus, name='reset_bus'),
# ]