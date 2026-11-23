import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.utils import timezone
from core.ai_service import GeminiAIService
from core.models import AuditLog
from core.utils import log_audit
from mortgages.models import MortgageApplication
from accounts.models import User


@csrf_exempt
@require_POST
def ai_chat_api(request):
    """
    Public & Authenticated AJAX endpoint for SunMortgages AI Financial Advisor chatbot.
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
        message = data.get("message", "").strip()
        history = data.get("history", [])

        if not message:
            return JsonResponse({"status": "error", "message": "Message cannot be empty."}, status=400)

        user_role = None
        user_name = None
        if request.user.is_authenticated:
            user_name = request.user.username
            user_role = request.user.get_role_display() if hasattr(request.user, "get_role_display") else request.user.role

        result = GeminiAIService.chat_with_advisor(
            message=message,
            history=history,
            user_role=user_role,
            user_name=user_name,
        )

        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@require_POST
def ai_underwrite_api(request, pk):
    """
    Staff-only endpoint: runs Google Gemini AI Credit Risk & Underwriting assessment.
    """
    if getattr(request.user, "role", None) != User.Role.STAFF and not request.user.is_staff:
        return JsonResponse({"status": "error", "message": "Unauthorized. Staff credentials required."}, status=403)

    application = get_object_or_404(
        MortgageApplication.objects.select_related("customer__user", "product"),
        pk=pk
    )

    try:
        assessment = GeminiAIService.generate_underwriting_assessment(application, actor=request.user)
        return JsonResponse({"status": "success", "assessment": assessment})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@require_POST
def ai_save_notes_api(request, pk):
    """
    Staff-only endpoint: appends AI underwriting assessment summary to staff notes.
    """
    if getattr(request.user, "role", None) != User.Role.STAFF and not request.user.is_staff:
        return JsonResponse({"status": "error", "message": "Unauthorized. Staff credentials required."}, status=403)

    application = get_object_or_404(MortgageApplication, pk=pk)

    try:
        data = json.loads(request.body.decode("utf-8"))
        notes_text = data.get("notes", "").strip()

        if not notes_text:
            return JsonResponse({"status": "error", "message": "No notes provided."}, status=400)

        timestamp_str = timezone.now().strftime("%d %b %Y %H:%M")
        memo_entry = f"\n\n--- [AI UNDERWRITING ASSESSMENT | {timestamp_str} | Verified by {request.user.username}] ---\n{notes_text}"

        application.staff_notes = (application.staff_notes or "") + memo_entry
        application.save(update_fields=["staff_notes", "updated_at"])

        log_audit(
            user=request.user,
            action=AuditLog.Action.UPDATE,
            model_name="MortgageApplication",
            object_id=str(application.id),
            details=f"AI Underwriting assessment saved to staff notes by {request.user.username}",
        )

        return JsonResponse({"status": "success", "message": "Assessment successfully saved to staff notes."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
