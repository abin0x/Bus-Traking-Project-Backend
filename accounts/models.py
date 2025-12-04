# accounts/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
import random

class User(AbstractUser):
    # ডিফল্ট username ফিল্ডটি আমরা student_id হিসেবে ব্যবহার করব
    full_name = models.CharField(max_length=255)
    student_id = models.CharField(max_length=7, unique=True, help_text="Must be 7 digits")
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    
    faculty = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    batch = models.CharField(max_length=10)
    
    # OTP ভেরিফিকেশনের জন্য
    otp = models.CharField(max_length=6, blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'student_id' # লগইনের জন্য আইডি ব্যবহার হবে
    REQUIRED_FIELDS = ['email', 'full_name', 'phone_number']

    def __str__(self):
        return f"{self.student_id} - {self.full_name}"

    def generate_otp(self):
        code = str(random.randint(100000, 999999))
        self.otp = code
        self.save()
        return code