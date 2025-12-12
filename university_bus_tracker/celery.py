import os
from celery import Celery

# জ্যাঙ্গো সেটিংস মডিউল সেট করা
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_bus_tracker.settings')

app = Celery('university_bus_tracker')

# জ্যাঙ্গো সেটিংস থেকে কনফিগারেশন নেওয়া (namespace='CELERY')
app.config_from_object('django.conf:settings', namespace='CELERY')

# অটোমেটিক টাস্ক লোড করা
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')