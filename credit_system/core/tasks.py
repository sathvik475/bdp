import pandas as pd
from celery import shared_task

from .models import Customer, Loan


@shared_task
def ingest_data():
    customer_df = pd.read_excel('customer_data.xlsx')
    loan_df = pd.read_excel('loan_data.xlsx')

    for _, row in customer_df.iterrows():
        Customer.objects.update_or_create(
            phone_number=row['phone_number'],
            defaults={
                'first_name': row['first_name'],
                'last_name': row['last_name'],
                'age': 30,  # Not provided in excel
                'monthly_income': row['monthly_salary'],
                'approved_limit': row['approved_limit'],
                'current_debt': row['current_debt']
            }
        )

    for _, row in loan_df.iterrows():
        Loan.objects.create(
            customer_id=row['customer id'],
            loan_amount=row['loan amount'],
            interest_rate=row['interest rate'],
            tenure=row['tenure'],
            monthly_installment=row['monthly repayment (emi)'],
            emis_paid_on_time=row['EMIs paid on time'],
            start_date=pd.to_datetime(row['start date']),
            end_date=pd.to_datetime(row['end date'])
        )
