from flask import Blueprint, render_template
from app.models import Ad, AdClick, AdImpression
from app.utils.db_helpers import safe_commit

ads_bp = Blueprint("ads", __name__)

@ads_bp.route("/impression/<int:ad_id>", methods=["POST"])
def track_impression(ad_id):
    impression = AdImpression(ad_id=ad_id)
    db.session.add(impression)
    safe_commit()
    return "", 204

@ads_bp.route("/ad/click/<int:ad_id>")
def ad_click(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    click = AdClick(ad_id=ad.id, user_id=current_user.id if current_user.is_authenticated else None)
    db.session.add(click)
    safe_commit()
    return redirect(ad.target_url)