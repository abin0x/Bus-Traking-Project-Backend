from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
from .serializers import RegistrationSerializer, VerifyOTPSerializer, LoginSerializer,  ForgotPasswordRequestSerializer, PasswordResetConfirmSerializer, UserProfileSerializer
from .data import FACULTY_DEPARTMENT_DATA
from django.contrib.auth import get_user_model
from django.contrib.auth import login , logout
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from rest_framework_simplejwt.tokens import RefreshToken
from django.template.loader import render_to_string # টেমপ্লেট রেন্ডার করার জন্য
from django.utils.html import strip_tags # HTML থেকে টেক্সট বের করার জন্য (ব্যাকআপ হিসেবে)


User = get_user_model()

# ==========================================
# 1. FACULTY DATA API (For Dropdowns)
# ==========================================
class FacultyDataView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(FACULTY_DEPARTMENT_DATA, status=status.HTTP_200_OK)


# ==========================================
# 2. REGISTRATION API (With SMTP Email)
# ==========================================


class StudentRegistrationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                user = serializer.save()
            except Exception as e:
                return Response({"error": "রেজিস্ট্রেশনে সমস্যা হয়েছে।"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            otp = user.generate_otp()
            
            # --- প্রফেশনাল HTML ইমেইল লজিক ---
            subject = 'HSTU Bus Tracker - Account Verification'
            context = {
                'full_name': user.full_name,
                'otp': otp
            }
            # HTML ফরম্যাট তৈরি করা
            html_message = render_to_string('otp_email.html', context)
            # যদি কারো ইমেইল ক্লায়েন্ট HTML সাপোর্ট না করে, তবে প্লেইন টেক্সট দেখাবে
            plain_message = strip_tags(html_message) 
            
            email_from = settings.EMAIL_HOST_USER 
            recipient_list = [user.email]
            
            email_sent = False
            try:
                send_mail(
                    subject, 
                    plain_message, 
                    email_from, 
                    recipient_list, 
                    html_message=html_message, # এই প্যারামিটারটি HTML মেইল পাঠাবে
                    fail_silently=False
                )
                email_sent = True
            except Exception as e:
                print(f"❌ Email Error: {e}")
                
            return Response({
                "status": "success",
                "message": "রেজিস্ট্রেশন সফল! ইমেইল চেক করুন।",
                "student_id": user.student_id,
                "email_sent": email_sent
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# 3. OTP VERIFICATION API
# ==========================================
class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        
        if serializer.is_valid():
            student_id = serializer.validated_data['student_id']
            input_otp = serializer.validated_data['otp']

            try:
                user = User.objects.get(student_id=student_id)

                if user.is_verified:
                    return Response({"status": "info", "message": "একাউন্ট ইতিমধ্যে ভেরিফাইড।"}, status=status.HTTP_200_OK)

                if user.otp == input_otp:
                    user.is_active = True   # Login Enable
                    user.is_verified = True # Verification Done
                    user.otp = None         # Clear OTP
                    user.save()
                    
                    return Response({
                        "status": "success",
                        "message": "ভেরিফিকেশন সফল! এখন লগইন করুন।"
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({"status": "error", "message": "ভুল OTP কোড।"}, status=status.HTTP_400_BAD_REQUEST)

            except User.DoesNotExist:
                return Response({"status": "error", "message": "ইউজার পাওয়া যায়নি।"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# 4. LOGIN API
# ==========================================
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            student_id = serializer.validated_data['student_id']
            password = serializer.validated_data['password']

            user = authenticate(username=student_id, password=password)

            if user is not None:
                if not user.is_verified:
                    return Response({"status": "error", "message": "Account not verified."}, status=status.HTTP_403_FORBIDDEN)
                
                # --- JWT টোকেন জেনারেট করা ---
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    "status": "success",
                    "message": "লগইন সফল হয়েছে!",
                    "access": str(refresh.access_token), # এটি অ্যাপ প্রতিবার API কলে পাঠাবে
                    "refresh": str(refresh), # এটি এক্সেস টোকেন এক্সপায়ার হলে নতুন টোকেন নিতে লাগবে
                    "user": {
                        "full_name": user.full_name,
                        "student_id": user.student_id
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({"status": "error", "message": "ভুল আইডি বা পাসওয়ার্ড।"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=400)
    
# ========================================== logout update api=======================
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # মোবাইল অ্যাপ বা ওয়েবসাইট থেকে রিফ্রেশ টোকেনটি পাঠাতে হবে
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            
            # টোকেনটিকে ব্ল্যাকলিস্টে পাঠিয়ে দেওয়া (যাতে এটি আর ব্যবহার না করা যায়)
            token.blacklist()
            
            return Response({"status": "success", "message": "Logout successful"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"status": "error", "message": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
    
# ========================================== frofile update api=======================
class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated] # শুধু লগইন করা ইউজার এক্সেস পাবে
    serializer_class = UserProfileSerializer

    def get_object(self):
        # যে ইউজার রিকোয়েস্ট পাঠাচ্ছে, শুধু তার প্রোফাইল রিটার্ন করবে
        return self.request.user

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [] 

    def post(self, request):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        if serializer.is_valid():
            student_id = serializer.validated_data['student_id']
            user = User.objects.get(student_id=student_id)

            # OTP তৈরি
            otp = user.generate_otp()

            # --- প্রফেশনাল HTML ইমেইল লজিক ---
            subject = 'HSTU Bus Tracker - Password Reset Request'
            context = {
                'full_name': user.full_name,
                'student_id': user.student_id,
                'otp': otp
            }
            
            # HTML এবং প্লেইন টেক্সট মেসেজ জেনারেট করা
            html_message = render_to_string('password_reset_email.html', context)
            plain_message = strip_tags(html_message)
            
            email_from = settings.EMAIL_HOST_USER
            recipient_list = [user.email]

            try:
                send_mail(
                    subject, 
                    plain_message, 
                    email_from, 
                    recipient_list, 
                    html_message=html_message, # HTML ফরম্যাট যুক্ত করা হলো
                    fail_silently=False
                )
                return Response({
                    "status": "success",
                    "message": "আপনার ইমেইলে একটি সিকিউরিটি কোড (OTP) পাঠানো হয়েছে।",
                    "student_id": student_id
                }, status=status.HTTP_200_OK)
            except Exception as e:
                print(f"❌ Reset Email Error: {e}")
                return Response({"error": "ইমেইল পাঠাতে সমস্যা হয়েছে। সার্ভার এরর।"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ==========================================
# 6. RESET PASSWORD - VERIFY OTP & CHANGE
# ==========================================
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            student_id = serializer.validated_data['student_id']
            otp = serializer.validated_data['otp']
            new_password = serializer.validated_data['new_password']

            try:
                user = User.objects.get(student_id=student_id)

                # OTP চেক
                if user.otp != otp:
                    return Response({"status": "error", "message": "ভুল OTP কোড!"}, status=status.HTTP_400_BAD_REQUEST)

                # পাসওয়ার্ড চেঞ্জ করা
                user.set_password(new_password)
                user.otp = None # OTP ক্লিয়ার করা (নিরাপত্তার জন্য)
                user.save()

                return Response({
                    "status": "success",
                    "message": "পাসওয়ার্ড সফলভাবে পরিবর্তন হয়েছে! এখন লগইন করুন।"
                }, status=status.HTTP_200_OK)

            except User.DoesNotExist:
                return Response({"status": "error", "message": "ইউজার পাওয়া যায়নি।"}, status=status.HTTP_404_NOT_FOUND)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)