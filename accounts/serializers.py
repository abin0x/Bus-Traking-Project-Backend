# accounts/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .data import FACULTY_DEPARTMENT_DATA
import re

User = get_user_model()

class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['full_name', 'student_id', 'phone_number', 'email', 'faculty', 'department', 'batch', 'password']

    # ১. ফোন নম্বর ভ্যালিডেশন (বাংলাদেশি নম্বর)
    def validate_phone_number(self, value):
        # প্যাটার্ন: +8801xxxxxxxxx অথবা 01xxxxxxxxx
        pattern = r'^(\+8801|01)[3-9]\d{8}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError("একটি সঠিক বাংলাদেশি মোবাইল নম্বর দিন (যেমন: 017xxxxxxxx)।")
        return value

    # ২. স্টুডেন্ট আইডি ভ্যালিডেশন (৭ ডিজিট)
    def validate_student_id(self, value):
        if not value.isdigit() or len(value) != 7:
            raise serializers.ValidationError("স্টুডেন্ট আইডি অবশ্যই ৭ সংখ্যার হতে হবে।")
        return value

    # ৩. ব্যাচ এবং ফ্যাকাল্টি চেক (Cross validation)
    def validate(self, data):
        student_id = data.get('student_id')
        batch = data.get('batch')
        faculty = data.get('faculty')
        department = data.get('department')

        # ব্যাচ ম্যাচিং লজিক (আইডি: 1902045 -> ব্যাচ: 19)
        if student_id and batch:
            id_prefix = student_id[:2] # প্রথম ২ ডিজিট
            if id_prefix != batch:
                raise serializers.ValidationError({"batch": f"ব্যাচ আইডির সাথে মিলছে না। আইডির শুরু {id_prefix} হলে ব্যাচও {id_prefix} হতে হবে।"})

        # ফ্যাকাল্টি এবং ডিপার্টমেন্ট চেক
        if faculty not in FACULTY_DEPARTMENT_DATA:
            raise serializers.ValidationError({"faculty": "অবৈধ ফ্যাকাল্টি নির্বাচন করা হয়েছে।"})
        
        if department not in FACULTY_DEPARTMENT_DATA[faculty]:
            raise serializers.ValidationError({"department": f"{faculty}-এর অধীনে এই ডিপার্টমেন্টটি নেই।"})

        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['student_id'], # Username = Student ID
            student_id=validated_data['student_id'],
            full_name=validated_data['full_name'],
            email=validated_data['email'],
            phone_number=validated_data['phone_number'],
            faculty=validated_data['faculty'],
            department=validated_data['department'],
            batch=validated_data['batch'],
            password=validated_data['password'],
            is_active=False, # ইমেইল ভেরিফিকেশন না হওয়া পর্যন্ত ইনএক্টিভ
            is_verified=False
        )
        return user

class VerifyOTPSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    otp = serializers.CharField(max_length=6)