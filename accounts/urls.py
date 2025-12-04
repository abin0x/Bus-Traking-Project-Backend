from django.urls import path
from .views import FacultyDataView, StudentRegistrationView, VerifyOTPView, LoginView

urlpatterns = [
    path('faculty-data/', FacultyDataView.as_view(), name='faculty_data'),
    path('register/', StudentRegistrationView.as_view(), name='register'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('login/', LoginView.as_view(), name='login'),
]