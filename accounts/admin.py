from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    কাস্টম ইউজার মডেলের জন্য অ্যাডমিন প্যানেল কনফিগারেশন।
    """
    model = User

    # ১. লিস্ট ভিউতে কী কী কলাম দেখাবে
    list_display = (
        'student_id', 
        'full_name', 
        'email', 
        'phone_number', 
        'department', 
        'batch',
        'verification_status', # কাস্টম ফাংশন (নিচে ডিফাইন করা)
        'is_active'
    )

    # ২. কোন কোন ফিল্ড দিয়ে সার্চ করা যাবে
    search_fields = ('student_id', 'full_name', 'email', 'phone_number')

    # ৩. ডান পাশে ফিল্টার অপশন
    list_filter = ('is_verified', 'is_active', 'faculty', 'department', 'batch')

    # ৪. ডিফল্ট অর্ডারিং (স্টুডেন্ট আইডি অনুযায়ী)
    ordering = ('student_id',)

    # ৫. ইউজার এডিট করার সময় ফর্মের লেআউট (Fieldsets)
    # যেহেতু username নেই, তাই student_id ব্যবহার করছি
    fieldsets = (
        ('Login Credentials', {
            'fields': ('student_id', 'password')
        }),
        ('Personal Information', {
            'fields': ('full_name', 'email', 'phone_number')
        }),
        ('Academic Information', {
            'fields': ('faculty', 'department', 'batch')
        }),
        ('Verification Status', {
            'fields': ('otp', 'is_verified')
        }),
        ('Permissions & Status', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',) # এই সেকশনটি হাইড করা থাকবে, ক্লিক করলে খুলবে
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )

    # ৬. নতুন ইউজার তৈরি করার সময় ফর্মের লেআউট
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('student_id', 'email', 'password', 'confirm_password'),
        }),
    )

    # ৭. OTP ফিল্ডটি অ্যাডমিন প্যানেলে Read Only রাখা ভালো (সিকিউরিটির জন্য)
    # তবে ডিবাগিংয়ের জন্য আপাতত এডিটেবল রাখতে পারেন। চাইলে নিচের লাইনটি আন-কমেন্ট করুন।
    # readonly_fields = ('otp', 'last_login', 'date_joined')

    # ৮. কাস্টম মেথড: ভেরিফিকেশন স্ট্যাটাস কালারফুল করে দেখানো
    def verification_status(self, obj):
        if obj.is_verified:
            return format_html(
                '<span style="background-color:green; color:white; padding:3px 8px; border-radius:5px;">Verified</span>'
            )
        return format_html(
            '<span style="background-color:red; color:white; padding:3px 8px; border-radius:5px;">Pending</span>'
        )
    
    verification_status.short_description = 'Status' # কলামের নাম