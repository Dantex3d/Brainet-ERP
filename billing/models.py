from django.db import models
from schools.models import School

class Billing(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    billing_date = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Billing for {self.school.name} - {self.amount} on {self.billing_date.strftime('%Y-%m-%d')}"

class Subscription(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    dos = models.ForeignKey('schools.DirectorOfStudies', on_delete=models.CASCADE)
    duration = models.CharField(max_length=50)  # e.g. "1 Year", "6 Months"
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()

    def days_remaining(self):
        from django.utils import timezone
        today = timezone.now().date()
        if self.end_date < today:
            return 0
        return (self.end_date - today).days

    def __str__(self):
        return f"Subscription for {self.school.name} - {self.duration}"
    
class BillingLog(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)  # e.g. "processing", "delivered", "success"
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"BillingLog for {self.subscription.school.name} - {self.status} at {self.updated_at.strftime('%Y-%m-%d %H:%M:%S')}"    