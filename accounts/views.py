# accounts/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from .serializers import RegistrationSerializer, VerifyOTPSerializer
from .data import FACULTY_DEPARTMENT_DATA

User = get_user_model()

# ১. রেজিস্ট্রেশন ভিউ
class StudentRegistrationView(APIView):
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # OTP জেনারেট এবং ইমেইল পাঠানো
            otp = user.generate_otp()
            
            # ইমেইল ফাংশন
            subject = 'Verify your Bus Tracking Account'
            message = f'হ্যালো {user.full_name},\n\nআপনার ভেরিফিকেশন কোড হলো: {otp}\nএটি কারো সাথে শেয়ার করবেন না।'
            from_email = 'admin@hstu-bus.com'
            recipient_list = [user.email]
            
            try:
                send_mail(subject, message, from_email, recipient_list)
            except Exception as e:
                return Response({"message": "ইউজার তৈরি হয়েছে কিন্তু ইমেইল পাঠানো যায়নি।"}, status=status.HTTP_201_CREATED)

            return Response({
                "message": "রেজিস্ট্রেশন সফল! আপনার ইমেইলে একটি কোড পাঠানো হয়েছে।",
                "student_id": user.student_id
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ২. OTP ভেরিফিকেশন ভিউ
class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            student_id = serializer.validated_data['student_id']
            otp = serializer.validated_data['otp']

            try:
                user = User.objects.get(student_id=student_id)
                
                if user.is_verified:
                    return Response({"message": "একাউন্ট ইতিমধ্যে ভেরিফাইড।"}, status=status.HTTP_400_BAD_REQUEST)

                if user.otp == otp:
                    user.is_active = True  # একাউন্ট একটিভ হলো
                    user.is_verified = True
                    user.otp = None  # OTP মুছে ফেলা হলো
                    user.save()
                    return Response({"message": "অভিনন্দন! আপনার একাউন্ট ভেরিফাই হয়েছে। এখন লগইন করুন।"}, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "ভুল কোড দিয়েছেন।"}, status=status.HTTP_400_BAD_REQUEST)

            except User.DoesNotExist:
                return Response({"error": "ইউজার পাওয়া যায়নি।"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ৩. ফ্যাকাল্টি ডেটা পাওয়ার ভিউ (ফ্রন্টএন্ডের জন্য)
class FacultyDataView(APIView):
    def get(self, request):
        return Response(FACULTY_DEPARTMENT_DATA)