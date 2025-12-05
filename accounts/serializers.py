from rest_framework import serializers
from django.contrib.auth import get_user_model
from .data import FACULTY_DEPARTMENT_DATA
import re

User = get_user_model()

class RegistrationSerializer(serializers.ModelSerializer):
    # পাসওয়ার্ড মিনিমাম ৬ ক্যারেক্টার হতে হবে
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['full_name', 'student_id', 'phone_number', 'email', 'faculty', 'department', 'batch', 'password']

    # ১. ফোন নম্বর ভ্যালিডেশন (বাংলাদেশি নম্বর)
    def validate_phone_number(self, value):
        # 013-019 বা +8801... ফরম্যাট সাপোর্ট করবে
        pattern = r'^(\+8801|01)[3-9]\d{8}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError("একটি সঠিক বাংলাদেশি মোবাইল নম্বর দিন (যেমন: 017xxxxxxxx)।")
        return value

    # ২. স্টুডেন্ট আইডি ভ্যালিডেশন (৭ ডিজিট)
    def validate_student_id(self, value):
        if not value.isdigit() or len(value) != 7:
            raise serializers.ValidationError("স্টুডেন্ট আইডি অবশ্যই ৭ সংখ্যার হতে হবে।")
        return value

    # ৩. ক্রস ভ্যালিডেশন (ব্যাচ, ফ্যাকাল্টি, ডিপার্টমেন্ট)
    def validate(self, data):
        student_id = data.get('student_id')
        batch = data.get('batch')
        faculty = data.get('faculty')
        department = data.get('department')

        # ব্যাচ ম্যাচিং লজিক (ID: 2002045 -> Batch: 20)
        if student_id and batch:
            id_prefix = student_id[:2] # প্রথম ২ ডিজিট
            if id_prefix != batch:
                raise serializers.ValidationError({"batch": f"ব্যাচ আইডির সাথে মিলছে না। আপনার আইডি {student_id} হলে ব্যাচ {id_prefix} হতে হবে।"})

        # ফ্যাকাল্টি এবং ডিপার্টমেন্ট চেক
        if faculty not in FACULTY_DEPARTMENT_DATA:
            raise serializers.ValidationError({"faculty": "অবৈধ ফ্যাকাল্টি নির্বাচন করা হয়েছে।"})
        
        if department not in FACULTY_DEPARTMENT_DATA[faculty]:
            raise serializers.ValidationError({"department": f"'{faculty}'-এর অধীনে '{department}' ডিপার্টমেন্টটি নেই।"})

        return data

    def create(self, validated_data):
        # ইউজার তৈরি (Active=False থাকবে যতক্ষণ না OTP ভেরিফাই হয়)
        user = User.objects.create_user(
            student_id=validated_data['student_id'],
            full_name=validated_data['full_name'],
            email=validated_data['email'],
            phone_number=validated_data['phone_number'],
            faculty=validated_data['faculty'],
            department=validated_data['department'],
            batch=validated_data['batch'],
            password=validated_data['password'],
            is_active=False,  # Inactive initially
            is_verified=False
        )
        return user

class VerifyOTPSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    otp = serializers.CharField(max_length=6, min_length=6)

class LoginSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    password = serializers.CharField()


# accounts/serializers.py - নিচে এই ক্লাসগুলো যোগ করুন

class ForgotPasswordRequestSerializer(serializers.Serializer):
    student_id = serializers.CharField()

    def validate_student_id(self, value):
        # চেক করি এই আইডির স্টুডেন্ট আছে কি না
        if not User.objects.filter(student_id=value).exists():
            raise serializers.ValidationError("এই স্টুডেন্ট আইডির কোনো একাউন্ট পাওয়া যায়নি।")
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    otp = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(min_length=6)


# accounts/serializers.py - ফাইলে নিচের ক্লাসটি যোগ করুন

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # পাসওয়ার্ড বাদে বাকি সব ফিল্ড যা আপডেট করা যাবে
        fields = ['full_name', 'student_id', 'email', 'phone_number', 'faculty', 'department', 'batch']
        # স্টুডেন্ট আইডি কেউ চেঞ্জ করতে পারবে না
        read_only_fields = ['student_id']