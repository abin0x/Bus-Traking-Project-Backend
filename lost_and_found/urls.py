from django.urls import path
from .views import StudentLostItemListView

urlpatterns = [
    # স্টুডেন্টদের জন্য লিংক
    path('list/', StudentLostItemListView.as_view(), name='student_lost_list'),
]