import os
from django.core.asgi import get_asgi_application

# ১. এনভায়রনমেন্ট সেট করুন
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_bus_tracker.settings')

# ২. আগে ডিজেঙ্গো অ্যাপ রেজিস্ট্রি লোড করুন
django_asgi_app = get_asgi_application()

# ৩. অ্যাপ লোড হওয়ার পর মডেল-নির্ভর জিনিসগুলো ইম্পোর্ট করুন
from channels.routing import ProtocolTypeRouter, URLRouter
import core.routing
from core.middleware import TokenAuthMiddleware

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": TokenAuthMiddleware(
        URLRouter(
            core.routing.websocket_urlpatterns
        )
    ),
})