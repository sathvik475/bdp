from datetime import datetime, timedelta
from math import pow

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Customer, Loan


def calculate_emi(principal, rate, tenure):
    r = rate / (12 * 100)
    emi = principal * r * pow(1 + r, tenure) / (pow(1 + r, tenure) - 1)
    return round(emi, 2)


class RegisterCustomerView(APIView):
    def post(self, request):
        try:
            data = request.data
            income = int(data.get('monthly_income'))
            approved_limit = round((36 * income) / 100000) * 100000

            customer = Customer.objects.create(
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                age=int(data.get('age')),
                monthly_income=income,
                approved_limit=approved_limit,
                phone_number=int(data.get('phone_number')),
                current_debt=0  # Set default if not included
            )

            return Response({
                "customer_id": customer.id,
                "name": f"{customer.first_name} {customer.last_name}",
                "age": customer.age,
                "monthly_income": customer.monthly_income,
                "approved_limit": customer.approved_limit,
                "phone_number": customer.phone_number
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CheckEligibilityView(APIView):
    def post(self, request):
        data = request.data
        customer = get_object_or_404(Customer, id=data['customer_id'])

        loans = Loan.objects.filter(customer=customer)
        current_year = datetime.now().year

        # Criteria:
        past_loans_paid_on_time = sum(loan.emis_paid_on_time for loan in loans)
        total_loans = loans.count()
        current_year_loans = loans.filter(start_date__year=current_year).count()
        total_loan_amount = sum(loan.loan_amount for loan in loans)

        # Over credit limit check
        if customer.current_debt > customer.approved_limit:
            credit_score = 0
        else:
            credit_score = min(100, (
                (past_loans_paid_on_time * 2)
                - (total_loans * 1)
                + (current_year_loans * 3)
                - (total_loan_amount // 100000)
            ))
            credit_score = max(0, credit_score)

        requested_amount = float(data['loan_amount'])
        requested_rate = float(data['interest_rate'])
        tenure = int(data['tenure'])
        monthly_installment = calculate_emi(requested_amount, requested_rate, tenure)

        corrected_rate = requested_rate
        approval = True

        # Apply credit rating rules
        if credit_score > 50:
            corrected_rate = requested_rate
        elif 30 < credit_score <= 50:
            corrected_rate = max(requested_rate, 12)
        elif 10 < credit_score <= 30:
            corrected_rate = max(requested_rate, 16)
        else:
            approval = False
            corrected_rate = None

        # Check EMI burden
        all_emis = sum(loan.monthly_installment for loan in loans)
        if (all_emis + monthly_installment) > (0.5 * customer.monthly_income):
            approval = False

        return Response({
            "customer_id": customer.id,
            "approval": approval,
            "interest_rate": requested_rate,
            "corrected_interest_rate": corrected_rate,
            "tenure": tenure,
            "monthly_installment": monthly_installment if approval else None
        })


class CreateLoanView(APIView):
    def post(self, request):
        data = request.data
        customer = get_object_or_404(Customer, id=data['customer_id'])

        # Reuse eligibility logic
        eligibility_request = {
            "customer_id": data['customer_id'],
            "loan_amount": data['loan_amount'],
            "interest_rate": data['interest_rate'],
            "tenure": data['tenure']
        }

        eligibility_view = CheckEligibilityView()
        eligibility_response = eligibility_view.post(request).data

        if not eligibility_response['approval']:
            return Response({
                "loan_id": None,
                "customer_id": customer.id,
                "loan_approved": False,
                "message": "Loan not approved",
                "monthly_installment": None
            })

        start_date = datetime.today().date()
        end_date = start_date + timedelta(days=30 * int(data['tenure']))
        loan = Loan.objects.create(
            customer=customer,
            loan_amount=data['loan_amount'],
            interest_rate=eligibility_response['corrected_interest_rate'],
            tenure=data['tenure'],
            monthly_installment=eligibility_response['monthly_installment'],
            emis_paid_on_time=0,
            start_date=start_date,
            end_date=end_date
        )

        customer.current_debt += float(data['loan_amount'])
        customer.save()

        return Response({
            "loan_id": loan.id,
            "customer_id": customer.id,
            "loan_approved": True,
            "message": "Loan approved",
            "monthly_installment": loan.monthly_installment
        })


class ViewLoanView(APIView):
    def get(self, request, loan_id):
        loan = get_object_or_404(Loan, id=loan_id)
        customer = loan.customer
        return Response({
            "loan_id": loan.id,
            "customer": {
                "id": customer.id,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "phone_number": customer.phone_number,
                "age": customer.age
            },
            "loan_amount": loan.loan_amount,
            "interest_rate": loan.interest_rate,
            "monthly_installment": loan.monthly_installment,
            "tenure": loan.tenure
        })


class ViewLoansByCustomer(APIView):
    def get(self, request, customer_id):
        customer = get_object_or_404(Customer, id=customer_id)
        loans = Loan.objects.filter(customer=customer)

        loan_list = []
        for loan in loans:
            repayments_left = loan.tenure - loan.emis_paid_on_time
            loan_list.append({
                "loan_id": loan.id,
                "loan_amount": loan.loan_amount,
                "interest_rate": loan.interest_rate,
                "monthly_installment": loan.monthly_installment,
                "repayments_left": repayments_left
            })

        return Response(loan_list)
