# university_bus_tracker/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # ১. অ্যাডমিন প্যানেল (http://127.0.0.1:8000/admin/)
    path('admin/', admin.site.urls),

    # ২. আমাদের অ্যাপের সব URL এখানে ইনক্লুড করা হলো
    path('', include('core.urls')),
    path('api/auth/', include('accounts.urls')),
]