from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static

from university_bus_tracker import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('api/auth/', include('accounts.urls')),
    path('api/lost-found/', include('lost_and_found.urls')),
    # path('sentry-debug/', trigger_error),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)