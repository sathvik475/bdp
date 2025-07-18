from django.db import models

class Customer(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    age = models.IntegerField()
    phone_number = models.BigIntegerField(unique=True)
    monthly_income = models.IntegerField()
    approved_limit = models.IntegerField()
    current_debt = models.FloatField(default=0)

class Loan(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    loan_amount = models.FloatField()
    interest_rate = models.FloatField()
    tenure = models.IntegerField()
    monthly_installment = models.FloatField()
    emis_paid_on_time = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
