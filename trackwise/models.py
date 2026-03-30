from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age = models.IntegerField(null=True, blank=True)
    city = models.CharField(max_length=100)
    occupation = models.CharField(max_length=100, blank=True, default='')

    def __str__(self):
        return self.user.username

class Category(models.Model):
    TYPE_CHOICES = [
        ('Income', 'Income'),
        ('Expense', 'Expense'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default='category', help_text="Material Symbol icon name")
    color_class = models.CharField(max_length=50, default='bg-slate-100 text-slate-600', help_text="Tailwind color classes")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='Expense')

    def __str__(self):
        return f"{self.name} ({self.type})"

class Budget(models.Model):
    category = models.OneToOneField(Category, on_delete=models.CASCADE)
    amount_limit = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.category.name} - ₹{self.amount_limit}"

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('Income', 'Income'),
        ('Expense', 'Expense'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    date = models.DateField()

    def __str__(self):
        return f"{self.date} - {self.description} (₹{self.amount})"

class EMI(models.Model):
    FREQUENCY_CHOICES = [
        ('Weekly', 'Weekly'),
        ('Monthly', 'Monthly'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='Monthly')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.description} - ₹{self.amount} ({self.frequency})"
