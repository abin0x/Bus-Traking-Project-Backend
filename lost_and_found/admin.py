from django.contrib import admin
from datetime import date, timedelta
from django.utils.translation import gettext_lazy as _
from .models import LostItem
from django.utils import timezone

# কাস্টম ডেট ফিল্টার (এডমিনের সুবিধার জন্য)
class DateFilter(admin.SimpleListFilter):
    title = _('Date Range')
    parameter_name = 'created_at'

    def lookups(self, request, model_admin):
        return (
            ('7days', _('Last 7 Days (App Visible)')),
            ('30days', _('Last 30 Days')),
        )

    def queryset(self, request, queryset):
        if self.value() == '7days':
            return queryset.filter(created_at__gte=date.today() - timedelta(days=7))
        if self.value() == '30days':
            return queryset.filter(created_at__gte=date.today() - timedelta(days=30))

@admin.register(LostItem)
class LostItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'contact_number', 'is_returned', 'is_visible_on_app')
    list_filter = ('is_returned', DateFilter) # আমাদের কাস্টম ফিল্টার এখানে যোগ করলাম
    search_fields = ('title', 'description')
    
    # এডমিন প্যানেলেই দেখাবে এই পোস্টটি অ্যাপে দেখা যাচ্ছে কি না
    def is_visible_on_app(self, obj):
        limit = timezone.now() - timedelta(days=7)
        return obj.created_at >= limit
    is_visible_on_app.boolean = True
    is_visible_on_app.short_description = "Visible on App?"