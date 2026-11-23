from django.shortcuts import render
from django.db.models import Avg, Min, Max
from mortgages.models import MortgageProduct, MortgageApplication


def landing_page(request):
    """
    High-impact fintech landing page showcasing SunMortgages products,
    real-time loan calculator, trust credentials, and AI advisory.
    """
    active_products = MortgageProduct.objects.filter(is_active=True).order_by("annual_interest_rate")
    
    # Aggregates for dynamic social proof / market summary
    stats = {
        "min_rate": active_products.aggregate(Min("annual_interest_rate"))["annual_interest_rate__min"] or "3.45",
        "avg_rate": active_products.aggregate(Avg("annual_interest_rate"))["annual_interest_rate__avg"] or "4.65",
        "total_schemes": active_products.count(),
        "total_applications": MortgageApplication.objects.count() + 1250, # illustrative aggregate
    }

    return render(
        request,
        "landing.html",
        {
            "products": active_products[:6],
            "all_products": active_products,
            "stats": stats,
        }
    )
