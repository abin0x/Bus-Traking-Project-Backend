from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
from .serializers import RegistrationSerializer, VerifyOTPSerializer, LoginSerializer
from .data import FACULTY_DEPARTMENT_DATA
from django.contrib.auth import get_user_model

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

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            # ১. ইউজার সেভ করা
            try:
                user = serializer.save()
            except Exception as e:
                return Response({"error": "রেজিস্ট্রেশনে সমস্যা হয়েছে। আবার চেষ্টা করুন।"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # ২. OTP জেনারেট করা
            otp = user.generate_otp()
            
            # ৩. SMTP দিয়ে ইমেইল পাঠানো
            subject = 'HSTU Bus Tracker - Account Verification'
            message = f'''হ্যালো {user.full_name},

আপনার বাস ট্র্যাকিং অ্যাপের ভেরিফিকেশন কোড (OTP) হলো: {otp}

দয়া করে অ্যাপে এই কোডটি দিয়ে আপনার একাউন্ট চালু করুন।

ধন্যবাদ,
এডমিন প্যানেল'''
            
            # settings.py থেকে হোস্ট ইমেইল নেওয়া
            email_from = settings.EMAIL_HOST_USER 
            recipient_list = [user.email]
            
            email_sent = False
            try:
                send_mail(subject, message, email_from, recipient_list, fail_silently=False)
                email_sent = True
            except Exception as e:
                # ইমেইল ফেইল হলে ইউজারকে জানানো, তবে একাউন্ট তৈরি থাকবে
                print(f"❌ Email Error: {e}")
                
            response_data = {
                "status": "success",
                "message": "রেজিস্ট্রেশন সফল!",
                "student_id": user.student_id,
                "email_sent": email_sent
            }
            
            if not email_sent:
                response_data["warning"] = "ইমেইল পাঠানো যায়নি। দয়া করে এডমিনের সাথে যোগাযোগ করুন বা পুনরায় চেষ্টা করুন।"

            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# 3. OTP VERIFICATION API
# ==========================================
class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

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

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            student_id = serializer.validated_data['student_id']
            password = serializer.validated_data['password']

            # Django Authenticate (Username Field = student_id)
            user = authenticate(username=student_id, password=password)

            if user is not None:
                # ১. ভেরিফিকেশন চেক
                if not user.is_verified:
                    return Response({
                        "status": "error",
                        "message": "আপনার একাউন্ট ভেরিফাইড নয়। দয়া করে OTP ভেরিফাই করুন।"
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # ২. একটিভ চেক
                if not user.is_active:
                    return Response({
                        "status": "error",
                        "message": "একাউন্টটি ব্লক বা নিষ্ক্রিয় করা হয়েছে।"
                    }, status=status.HTTP_403_FORBIDDEN)

                # ৩. সফল লগইন
                return Response({
                    "status": "success",
                    "message": "লগইন সফল হয়েছে!",
                    "user": {
                        "full_name": user.full_name,
                        "student_id": user.student_id,
                        "faculty": user.faculty,
                        "department": user.department
                    }
                    # ভবিষ্যতে এখানে JWT Token (access/refresh) যোগ করবেন
                }, status=status.HTTP_200_OK)

            else:
                return Response({"status": "error", "message": "ভুল স্টুডেন্ট আইডি অথবা পাসওয়ার্ড।"}, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)