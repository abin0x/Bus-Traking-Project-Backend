# accounts/urls.py

from django.urls import path
from .views import StudentRegistrationView, VerifyOTPView, FacultyDataView

urlpatterns = [
    path('register/', StudentRegistrationView.as_view(), name='register'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('faculty-data/', FacultyDataView.as_view(), name='faculty_data'), # ড্রপডাউন পপুলেট করার জন্য
]