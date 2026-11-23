from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .services import BankGatewayService
from .models import ApiRequestLog


class BankAccountVerificationAPIView(APIView):
    """
    API Endpoint: Verify customer bank account via Banking Gateway.
    POST Payload: { "bank_name": "Nabil Bank", "account_number": "0123456789", "account_name": "Sarah Jenkins" }
    """
    def post(self, request):
        bank_name = request.data.get("bank_name")
        account_number = request.data.get("account_number")
        account_name = request.data.get("account_name")

        if not all([bank_name, account_number, account_name]):
            return Response(
                {"error": "bank_name, account_number, and account_name are all required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = BankGatewayService()
        result = service.verify_account(bank_name, account_number, account_name)
        status_code = status.HTTP_200_OK if result["success"] else status.HTTP_404_NOT_FOUND
        return Response(result, status=status_code)


class BankMarketRatesAPIView(APIView):
    """
    API Endpoint: Retrieve partner bank benchmark mortgage interest rates.
    """
    def get(self, request):
        service = BankGatewayService()
        rates = service.fetch_market_interest_rates()
        return Response({
            "provider": service.partner.name,
            "mode": "Sandbox/Simulated" if service.partner.is_mock else "Production",
            "base_rates": rates
        })


class BankCreditAssessmentAPIView(APIView):
    """
    API Endpoint: Instant automated credit bureau score and DTI assessment.
    POST Payload: { "monthly_income": 8500, "requested_amount": 250000, "term_years": 25 }
    """
    def post(self, request):
        try:
            monthly_income = float(request.data.get("monthly_income", 0))
            requested_amount = float(request.data.get("requested_amount", 0))
            term_years = int(request.data.get("term_years", 25))

            if monthly_income <= 0 or requested_amount <= 0 or term_years <= 0:
                return Response(
                    {"error": "Positive numbers required for monthly_income, requested_amount, and term_years."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            service = BankGatewayService()
            assessment = service.check_credit_eligibility(monthly_income, requested_amount, term_years)
            return Response(assessment)
        except (ValueError, TypeError) as e:
            return Response({"error": f"Invalid numeric input: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
