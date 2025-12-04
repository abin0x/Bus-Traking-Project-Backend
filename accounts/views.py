from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate, get_user_model
from django.core.mail import send_mail
from django.conf import settings

# আপনার তৈরি করা Serializers এবং Data ইম্পোর্ট করা
from .serializers import RegistrationSerializer, VerifyOTPSerializer
from .data import FACULTY_DEPARTMENT_DATA

User = get_user_model()

# ==========================================
# 1. FACULTY DATA API (For Dropdowns)
# ==========================================
class FacultyDataView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        """
        রেজিস্ট্রেশন পেইজে ফ্যাকাল্টি এবং ডিপার্টমেন্ট লোড করার জন্য।
        """
        return Response(FACULTY_DEPARTMENT_DATA, status=status.HTTP_200_OK)


# ==========================================
# 2. REGISTRATION API
# ==========================================
class StudentRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            # ১. ইউজার সেভ করা (is_active=False অবস্থায়)
            user = serializer.save()
            
            # ২. OTP জেনারেট করা
            otp = user.generate_otp()
            
            # ৩. ইমেইল পাঠানো
            subject = 'HstuBus - Account Verification'
            message = f'হ্যালো {user.full_name},\n\nআপনার ভেরিফিকেশন কোড (OTP) হলো: {otp}\n\nধন্যবাদ,\nবাস ট্র্যাকিং টিম।'
            email_from = settings.EMAIL_HOST_USER or 'noreply@hstubus.com'
            recipient_list = [user.email]
            
            try:
                send_mail(subject, message, email_from, recipient_list)
                email_status = "Email sent successfully."
            except Exception as e:
                print(f"Email Error: {e}")
                email_status = "Failed to send email. Check server logs."

            return Response({
                "status": "success",
                "message": "রেজিস্ট্রেশন সফল! আপনার ইমেইলে কোড পাঠানো হয়েছে।",
                "email_status": email_status,
                "student_id": user.student_id
            }, status=status.HTTP_201_CREATED)
        
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

                # যদি অলরেডি ভেরিফাইড থাকে
                if user.is_verified:
                    return Response({"status": "info", "message": "একাউন্ট ইতিমধ্যে ভেরিফাইড। লগইন করুন।"}, status=status.HTTP_200_OK)

                # OTP ম্যাচিং
                if user.otp == input_otp:
                    user.is_active = True   # একাউন্ট চালু হলো
                    user.is_verified = True # ভেরিফাইড হলো
                    user.otp = None         # OTP মুছে ফেলা হলো (সিকিউরিটির জন্য)
                    user.save()
                    
                    return Response({
                        "status": "success",
                        "message": "ভেরিফিকেশন সফল! এখন আপনি লগইন করতে পারবেন।"
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({"status": "error", "message": "ভুল কোড! আবার চেষ্টা করুন।"}, status=status.HTTP_400_BAD_REQUEST)

            except User.DoesNotExist:
                return Response({"status": "error", "message": "ইউজার পাওয়া যায়নি।"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# 4. LOGIN API
# ==========================================
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        student_id = request.data.get('student_id')
        password = request.data.get('password')

        if not student_id or not password:
            return Response({"error": "Student ID এবং Password দিতে হবে।"}, status=status.HTTP_400_BAD_REQUEST)

        # Django Authenticate ফাংশন কল করা
        # আমরা মডেলে USERNAME_FIELD = 'student_id' সেট করেছি, তাই 'username' প্যারামিটারে আইডি পাঠাতে হবে
        user = authenticate(username=student_id, password=password)

        if user is not None:
            if not user.is_verified:
                return Response({"error": "আপনার একাউন্ট ভেরিফাইড নয়। দয়া করে OTP ভেরিফাই করুন।"}, status=status.HTTP_403_FORBIDDEN)
            
            if not user.is_active:
                return Response({"error": "একাউন্টটি ব্লক করা হয়েছে।"}, status=status.HTTP_403_FORBIDDEN)

            # লগইন সফল
            # (ভবিষ্যতে এখানে JWT Token রিটার্ন করতে পারেন। আপাতত বেসিক ডেটা পাঠানো হলো)
            return Response({
                "status": "success",
                "message": "লগইন সফল হয়েছে!",
                "user": {
                    "full_name": user.full_name,
                    "student_id": user.student_id,
                    "department": user.department,
                    "is_superuser": user.is_superuser
                }
            }, status=status.HTTP_200_OK)

        else:
            return Response({"error": "ভুল স্টুডেন্ট আইডি অথবা পাসওয়ার্ড।"}, status=status.HTTP_401_UNAUTHORIZED)