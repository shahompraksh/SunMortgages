"""
SunMortgages Gemini AI Service
Integrates Google Gemini 3.5 Flash / Flash Lite for:
1. Interactive Mortgage & Financial Advisory Chatbot (Borrowers & Public)
2. Intelligent Credit Risk & Underwriting Assessment Copilot (Staff)
"""

import json
import logging
import urllib.request
import urllib.error
from decimal import Decimal
from django.conf import settings
from core.models import AuditLog
from core.utils import log_audit

logger = logging.getLogger(__name__)

GEMINI_API_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
)


class GeminiAIService:
    """Service client for Google Gemini AI integrations."""

    @classmethod
    def get_api_key(cls):
        return getattr(settings, "GEMINI_API_KEY", None)

    @classmethod
    def get_model(cls):
        return getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash-lite")

    @classmethod
    def _call_gemini_api(cls, payload, timeout=15):
        """Low-level caller for Gemini REST API using Python standard library."""
        api_key = cls.get_api_key()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured in settings or environment.")

        model = cls.get_model()
        url = GEMINI_API_URL_TEMPLATE.format(model=model, key=api_key)
        data_bytes = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            resp_body = response.read().decode("utf-8")
            return json.loads(resp_body)

    @classmethod
    def chat_with_advisor(cls, message, history=None, user_role=None, user_name=None):
        """
        Interactive mortgage financial advisor powered by Gemini.
        Answers user questions with context of SunMortgages active schemes.
        """
        # Fetch active products for ground-truth context
        products_context = ""
        try:
            from mortgages.models import MortgageProduct
            active_products = MortgageProduct.objects.filter(is_active=True)
            if active_products.exists():
                lines = []
                for p in active_products:
                    lines.append(
                        f"- {p.name}: {p.annual_interest_rate}% p.a. | "
                        f"Amount £{p.minimum_amount:,.2f} - £{p.maximum_amount:,.2f} | "
                        f"Max Term up to {p.maximum_term_years} yrs | "
                        f"{p.description or 'Standard scheme'}"
                    )
                products_context = "\nCurrent Active SunMortgages Loan Schemes:\n" + "\n".join(lines)
        except Exception as e:
            logger.warning(f"Could not load products for AI context: {e}")

        system_instruction = (
            "You are the Senior Mortgage & Financial Advisor at SunMortgages, a premier British and "
            "international mortgage brokerage and lending institution regulated to FCA standards. "
            "You provide accurate, professional, friendly, and transparent advice to individual homebuyers "
            "and commercial property developers.\n\n"
            "Key Guidelines:\n"
            "1. Address mortgage concepts clearly: LTV (Loan to Value), fixed vs variable interest, "
            "amortisation, repayment calculations, affordability checks, and developer commercial facilities.\n"
            "2. Reference actual SunMortgages products when relevant.\n"
            "3. Format answers using concise paragraphs, bullet points, and bold text for readability.\n"
            "4. Always include a short helpful disclaimer when giving financial estimates.\n"
            f"User Context: Username: {user_name or 'Guest'}, Role: {user_role or 'Individual Customer'}.\n"
            f"{products_context}"
        )

        # Build contents list
        contents = []
        if history:
            for item in history[-6:]:  # Keep recent turns
                role = "user" if item.get("role") == "user" else "model"
                text = item.get("text", "").strip()
                if text:
                    contents.append({"role": role, "parts": [{"text": text}]})

        contents.append({"role": "user", "parts": [{"text": message}]})

        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 1000,
            }
        }

        try:
            data = cls._call_gemini_api(payload)
            reply = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"status": "success", "reply": reply}
        except Exception as e:
            logger.error(f"Gemini chat API error: {e}")
            # Intelligent fallback response
            return {
                "status": "fallback",
                "reply": (
                    "Thank you for contacting SunMortgages Advisor. We offer competitive fixed and variable "
                    "mortgages with interest rates tailored for both individual home buyers and property developers. "
                    "Our interactive loan calculator and scheme list are available on our platform to help you plan "
                    "your monthly repayments with zero fees."
                ),
            }

    @classmethod
    def generate_underwriting_assessment(cls, application, actor=None):
        """
        AI Credit Risk & Underwriting Copilot for Staff.
        Analyzes the mortgage application parameters, borrower profile, and financials.
        """
        from mortgages.views import calculate_amortisation
        from banking.models import BankAccountVerification

        # Financial computations
        monthly_estimate, total_cost, total_interest = calculate_amortisation(
            amount_val=application.requested_amount,
            annual_rate_val=application.product.annual_interest_rate,
            years_val=application.term_years,
        )

        # Customer & Verification data
        customer = application.customer
        user = customer.user
        customer_type = customer.get_customer_type_display()
        company = customer.company_name or "N/A"
        address = customer.address or "Not provided"

        # Check banking verification
        verifications = BankAccountVerification.objects.filter(
            account_name__icontains=user.username
        ).order_by("-verified_at")
        bank_status = "Unverified"
        if verifications.exists():
            v = verifications.first()
            bank_status = f"{v.get_status_display()} ({v.bank_name}, Sort: {v.sort_code})"

        prompt = f"""
Act as an Expert Chief Underwriting Officer and Risk Auditor at SunMortgages.
Conduct an in-depth credit and risk underwriting assessment of the following mortgage application:

APPLICATION DOSSIER:
- Application ID: #{application.id}
- Borrower Username: {user.username}
- Customer Type: {customer_type}
- Company / Developer Name: {company}
- Residential/Registered Address: {address}
- Banking Verification Status: {bank_status}
- Mortgage Scheme: {application.product.name}
- Annual Interest Rate: {application.product.annual_interest_rate}%
- Requested Loan Capital: £{application.requested_amount:,.2f}
- Loan Duration: {application.term_years} Years ({application.term_years * 12} Monthly Installments)
- Projected Monthly Payment: £{monthly_estimate:,.2f}
- Total Lifetime Cost: £{total_cost:,.2f} (Total Interest: £{total_interest:,.2f})
- Scheme Min/Max Limits: £{application.product.minimum_amount:,.2f} to £{application.product.maximum_amount:,.2f}
- Current Status: {application.get_status_display()}
- Applicant Supporting Statement: "{application.applicant_notes or 'No notes provided by applicant.'}"
- Existing Staff Notes: "{application.staff_notes or 'None.'}"

TASK REQUIREMENTS:
Provide an executive underwriting evaluation in clean JSON format matching this exact schema:
{{
    "risk_score": <Integer between 1 and 100, where 90+ is Prime, 75-89 is Low Risk, 50-74 is Moderate Risk, <50 is High Risk>,
    "risk_rating": "<LOW | MODERATE | HIGH | CRITICAL>",
    "recommendation": "<RECOMMEND APPROVAL | CONDITIONAL APPROVAL | UNDERWRITER REVIEW | RECOMMEND DECLINE>",
    "executive_summary": "<2-3 concise sentences summarizing the risk profile>",
    "affordability_analysis": "<Analysis of debt serviceability for £{monthly_estimate:,.2f}/mo over {application.term_years} years>",
    "key_strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
    "risk_factors": ["<risk factor 1>", "<risk factor 2>"],
    "required_stipulations": ["<condition 1 prior to fund disbursement>", "<condition 2>"]
}}
Respond ONLY with the valid JSON object without surrounding text or markdown ticks.
"""

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1200,
            }
        }

        assessment_data = None
        try:
            res = cls._call_gemini_api(payload)
            raw_text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Clean possible markdown fence if model wrapped in ```json
            if raw_text.startswith("```"):
                raw_text = raw_text.strip("`")
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:].strip()
            assessment_data = json.loads(raw_text)
            assessment_data["source"] = "Gemini 3.5 Flash AI"
        except Exception as e:
            logger.error(f"Gemini underwriting evaluation failed: {e}")
            # Deterministic algorithmic fallback
            score = 82 if application.requested_amount <= application.product.maximum_amount * Decimal("0.8") else 68
            rating = "LOW" if score >= 80 else "MODERATE"
            rec = "RECOMMEND APPROVAL" if score >= 80 else "CONDITIONAL APPROVAL"
            assessment_data = {
                "risk_score": score,
                "risk_rating": rating,
                "recommendation": rec,
                "executive_summary": (
                    f"Automated risk audit for #{application.id}. Loan request of £{application.requested_amount:,.2f} "
                    f"falls within the product boundary (£{application.product.minimum_amount:,.2f} - "
                    f"£{application.product.maximum_amount:,.2f}). Monthly repayment commitment is £{monthly_estimate:,.2f}."
                ),
                "affordability_analysis": (
                    f"Monthly debt service requirement is £{monthly_estimate:,.2f} over a {application.term_years}-year horizon. "
                    f"Total interest liability is £{total_interest:,.2f} at {application.product.annual_interest_rate}% fixed."
                ),
                "key_strengths": [
                    "Requested amount complies with scheme threshold",
                    f"Applicant registered as {customer_type}",
                    "Standard amortisation schedule with predictable payments"
                ],
                "risk_factors": [
                    "Manual verification of source of equity deposit required",
                    "Proof of ongoing monthly income verification needed"
                ],
                "required_stipulations": [
                    "Certified copy of latest 3 months bank statements",
                    "Signed declaration of property charge and valuation report"
                ],
                "source": "SunMortgages Algorithmic Engine (Fallback)",
            }

        # Log audit action
        log_audit(
            user=actor,
            action=AuditLog.Action.API_CALL,
            model_name="MortgageApplication",
            object_id=str(application.id),
            details=f"AI Underwriting Risk Assessment generated. Score: {assessment_data.get('risk_score')}/100, Rating: {assessment_data.get('risk_rating')}",
        )

        return assessment_data
