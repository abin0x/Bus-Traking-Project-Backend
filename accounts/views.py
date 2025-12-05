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
                
                # [CRITICAL CHANGE] সার্ভারে সেশন তৈরি করা
                login(request, user)

                return Response({
                    "status": "success",
                    "message": "লগইন সফল হয়েছে!",
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
    def post(self, request):
        logout(request) # সার্ভার সেশন মুছে ফেলবে
        return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
    
# ========================================== frofile update api=======================
class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated] # শুধু লগইন করা ইউজার এক্সেস পাবে
    serializer_class = UserProfileSerializer

    def get_object(self):
        # যে ইউজার রিকোয়েস্ট পাঠাচ্ছে, শুধু তার প্রোফাইল রিটার্ন করবে
        return self.request.user

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [] # CSRF bypass

    def post(self, request):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        if serializer.is_valid():
            student_id = serializer.validated_data['student_id']
            user = User.objects.get(student_id=student_id)

            # OTP তৈরি ও সেভ করা
            otp = user.generate_otp()

            # ইমেইল পাঠানো
            subject = 'HSTU Bus Tracker - Password Reset Request'
            message = f'''প্রিয় {user.full_name},

আপনার পাসওয়ার্ড রিসেট করার জন্য নিচের OTP কোডটি ব্যবহার করুন:

OTP: {otp}

আপনি যদি এই রিকোয়েস্ট না করে থাকেন, তবে এটি ইগনোর করুন।

ধন্যবাদ,
এডমিন প্যানেল'''
            
            email_from = settings.EMAIL_HOST_USER
            recipient_list = [user.email]

            try:
                send_mail(subject, message, email_from, recipient_list, fail_silently=False)
                return Response({
                    "status": "success",
                    "message": "আপনার ইমেইলে একটি OTP পাঠানো হয়েছে।",
                    "student_id": student_id
                }, status=status.HTTP_200_OK)
            except Exception as e:
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