from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from .models import LostItem
from .serializers import LostItemSerializer

class StudentLostItemListView(generics.ListAPIView):
    serializer_class = LostItemSerializer
    # permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        # ১. বর্তমান সময়
        now = timezone.now()
        
        # ২. ৭ দিন আগের সময় বের করা
        seven_days_ago = now - timedelta(days=7)
        
        # ৩. ফিল্টার লজিক:
        # - created_at হতে হবে গত ৭ দিনের মধ্যে (__gte = Greater than or equal)
        # - is_returned হতে হবে False (ফেরত দেওয়া হয়নি)
        queryset = LostItem.objects.filter(
            created_at__gte=seven_days_ago,
            is_returned=False
        ).order_by('-created_at')
        
        return queryset
    
