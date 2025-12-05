from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
import random

# ১. কাস্টম ইউজার ম্যানেজার তৈরি (এটি এই এররটি ফিক্স করবে)
class CustomUserManager(BaseUserManager):
    def create_user(self, student_id, email, password=None, **extra_fields):
        if not student_id:
            raise ValueError('The Student ID must be set')
        if not email:
            raise ValueError('The Email must be set')
        
        email = self.normalize_email(email)
        user = self.model(student_id=student_id, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, student_id, email, password=None, **extra_fields):
        # সুপারইউজারের পারমিশন সেট করা
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(student_id, email, password, **extra_fields)

# ২. ইউজার মডেল
class User(AbstractUser):
    # ডিফল্ট username ফিল্ডটি বাদ দিচ্ছি
    username = None 

    full_name = models.CharField(max_length=255)
    student_id = models.CharField(max_length=7, unique=True, help_text="Must be 7 digits")
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    
    faculty = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    batch = models.CharField(max_length=10)
    profile_image = models.URLField(max_length=500, blank=True, null=True, help_text="Paste image link here")
    
    otp = models.CharField(max_length=6, blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    # কনফিগারেশন
    USERNAME_FIELD = 'student_id'  # এখন লগইনের জন্য Student ID লাগবে
    
    # সুপারইউজার তৈরির সময় এই ফিল্ডগুলো চাইবে
    REQUIRED_FIELDS = ['email', 'full_name', 'phone_number', 'faculty', 'department', 'batch']

    # [IMPORTANT] কাস্টম ম্যানেজার লিংক করা (এটি ছাড়া এরর আসবে)
    objects = CustomUserManager()

    def __str__(self):
        return f"{self.student_id} - {self.full_name}"

    def generate_otp(self):
        code = str(random.randint(100000, 999999))
        self.otp = code
        self.save()
        return code