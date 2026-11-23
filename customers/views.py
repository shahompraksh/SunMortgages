from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Q
from .models import CustomerProfile
from .forms import CustomerProfileForm


def staff_required(user):
    return user.is_authenticated and (user.is_staff or getattr(user, "role", "") == "STAFF")


@login_required
def my_profile(request):
    customer_type = (
        CustomerProfile.CustomerType.DEVELOPER
        if getattr(request.user, "role", "") == "DEVELOPER"
        else CustomerProfile.CustomerType.INDIVIDUAL
    )
    profile, created = CustomerProfile.objects.get_or_create(
        user=request.user,
        defaults={"customer_type": customer_type}
    )

    if request.method == "POST":
        form = CustomerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("my-profile")
    else:
        form = CustomerProfileForm(instance=profile)

    return render(request, "customers/my_profile.html", {
        "profile": profile,
        "form": form,
    })


@login_required
@user_passes_test(staff_required)
def customer_list(request):
    query = request.GET.get("q", "").strip()
    customers = CustomerProfile.objects.select_related(
        "user"
    ).order_by("-created_at")
    if query:
        customers = customers.filter(
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query) |
            Q(company_name__icontains=query)
        )
    return render(request, "customers/customer_list.html", {
        "customers": customers,
        "query": query,
    })


@login_required
@user_passes_test(staff_required)
def customer_detail(request, pk):
    customer = get_object_or_404(
        CustomerProfile.objects.select_related("user"),
        pk=pk
    )
    return render(request, "customers/customer_detail.html", {
        "customer": customer,
    })


@login_required
@user_passes_test(staff_required)
def customer_edit(request, pk):
    customer = get_object_or_404(CustomerProfile, pk=pk)
    if request.method == "POST":
        form = CustomerProfileForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, "Customer updated successfully.")
            return redirect("customer-detail", pk=pk)
    else:
        form = CustomerProfileForm(instance=customer)
    return render(request, "customers/customer_edit.html", {
        "form": form,
        "customer": customer,
    })


@login_required
@user_passes_test(staff_required)
@require_POST
def customer_delete(request, pk):
    customer = get_object_or_404(CustomerProfile, pk=pk)
    # Remove the profile, not the user's login account.
    customer.delete()
    messages.success(request, "Customer profile deleted.")
    return redirect("customer-list")
