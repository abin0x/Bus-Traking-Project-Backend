from django.db import models

class LostItem(models.Model):
    title = models.CharField(max_length=100) # কি হারিয়েছে?
    description = models.TextField()         # বিস্তারিত বিবরণ
    image_url = models.URLField(max_length=500, blank=True, null=True, help_text="ছবির লিংক দিন")
    contact_number = models.CharField(max_length=15, default="017xxxxxxxx") # অথরিটির নম্বর
    
    # অটোমেটিক তারিখ ও সময় সেভ হবে
    created_at = models.DateTimeField(auto_now_add=True)
    
    # যদি মালিক ফেরত পায়, তবে এডমিন এটি True করে দেবে
    is_returned = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} ({self.created_at.strftime('%Y-%m-%d')})"

    class Meta:
        ordering = ['-created_at'] # লেটেস্ট পোস্ট আগে দেখাবে