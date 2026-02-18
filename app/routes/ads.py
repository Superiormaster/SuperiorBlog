from flask import Blueprint, render_template
from app.models import Ad

ads_bp = Blueprint("ads", __name__)

def get_active_ads(location=None):
    """Fetch active ads optionally filtered by location."""
    query = Ad.query.filter_by(active=True)
    if location:
        query = query.filter_by(location=location)
    return query.all()

@ads_bp.route("/ad/click/<int:ad_id>")
@login_required(optional=True)
def ad_click(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    click = AdClick(ad_id=ad.id, user_id=current_user.id if current_user.is_authenticated else None)
    db.session.add(click)
    db.session.commit()
    return redirect(ad.target_url)



<!-- Sidebar Ads -->
<div class="sidebar-ads">
    {% for ad in get_active_ads('sidebar') %}
        <a href="{{ ad.target_url }}" target="_blank" class="block my-4 hover:shadow-lg transition">
            {% if ad.image_url %}
                <img src="{{ ad.image_url }}" alt="{{ ad.title }}" class="rounded w-full">
            {% else %}
                <div class="bg-gray-200 p-4 rounded text-center font-semibold">
                    {{ ad.title }}
                </div>
            {% endif %}
        </a>
    {% else %}
        <!-- No ads -->
        <div class="text-gray-400 text-sm">Ads will appear here after launch.</div>
    {% endfor %}
</div>



<div class="header-ads text-center my-2">
    {% for ad in get_active_ads('header') %}
        <a href="{{ ad.target_url }}" target="_blank">
            {% if ad.image_url %}
                <img src="{{ ad.image_url }}" alt="{{ ad.title }}" class="mx-auto rounded">
            {% else %}
                <span class="font-bold">{{ ad.title }}</span>
            {% endif %}
        </a>
    {% endfor %}
</div>



{% if show_ads %}
    {% include 'partials/sidebar_ads.html' %}
{% endif %}

