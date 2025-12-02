# core/urls.py

from django.urls import path
from django.views.generic import TemplateView
from .views import LocationUpdateView

urlpatterns = [
    # ১. ফ্রন্টএন্ড ড্যাশবোর্ড (Map UI)
    # ব্রাউজারে 'http://127.0.0.1:8000/' হিট করলে index.html দেখাবে
    path('', TemplateView.as_view(template_name='index.html'), name='home'),

    # ২. হাইব্রিড API এন্ডপয়েন্ট (GET & POST)
    # GET: ম্যাপ লোড হওয়ার সময় বাসের ইনিশিয়াল ডেটা আনে
    # POST: ESP32 থেকে জিপিএস ডেটা রিসিভ করে
    path('api/update-location/', LocationUpdateView.as_view(), name='update_location'),
]