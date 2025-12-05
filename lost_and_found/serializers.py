from rest_framework import serializers
from .models import LostItem

class LostItemSerializer(serializers.ModelSerializer):
    # স্টুডেন্টদের দেখানোর জন্য তারিখ সুন্দরভাবে ফরম্যাট করা
    found_date_display = serializers.SerializerMethodField()

    class Meta:
        model = LostItem
        fields = ['id', 'title', 'description', 'image_url', 'contact_number', 'found_date_display']

    def get_found_date_display(self, obj):
        return obj.created_at.strftime("%d %b, %I:%M %p") # 05 Dec, 02:30 PM