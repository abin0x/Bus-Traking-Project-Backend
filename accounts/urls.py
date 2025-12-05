from django.urls import path
from .views import FacultyDataView, StudentRegistrationView, VerifyOTPView, LoginView, ForgotPasswordView, ResetPasswordView, UserProfileView

urlpatterns = [
    path('faculty-data/', FacultyDataView.as_view(), name='faculty_data'),
    path('register/', StudentRegistrationView.as_view(), name='register'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('login/', LoginView.as_view(), name='login'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
]