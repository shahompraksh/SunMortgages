from .models import AuditLog


def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit(request=None, user=None, action=AuditLog.Action.CREATE, model_name="", object_id="", details=""):
    try:
        actor = user or (request.user if request and hasattr(request, "user") and request.user.is_authenticated else None)
        ip = get_client_ip(request) if request else None
        return AuditLog.objects.create(
            user=actor,
            action=action,
            model_name=model_name,
            object_id=str(object_id),
            details=details,
            ip_address=ip
        )
    except Exception:
        return None
