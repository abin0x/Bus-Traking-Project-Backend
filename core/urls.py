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