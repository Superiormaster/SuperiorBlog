import requests
from flask import Blueprint, render_template, request, jsonify, redirect
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db
from app.utils.db_helpers import safe_commit

billing_bp = Blueprint('billings', __name__)

@billing_bp.route("/paystack/init", methods=["POST"])
@login_required
def init_payment():
  try:
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "email": current_user.email,
        "amount": 200000  # ₦2,000
    }
    print("Payload:", data)
    print("Headers:", headers)

    r = requests.post(
        "https://api.paystack.co/transaction/initialize",
        json=data,
        headers=headers,
        timeout=20
    )
    print("Paystack response:", r.text)
    res = r.json()
    return res
  except Exception as e:
    print("Paystack init error:", e)
    return jsonify({"status": False, "message": "Payment initialization failed."}), 500

@billing_bp.route("/paystack/verify/<ref>")
@login_required
def verify(ref):
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    r = requests.get(
        f"https://api.paystack.co/transaction/verify/{ref}",
        headers=headers
    ).json()

    if r.get("status") == True and r["data"]["status"] == "success":
        current_user.is_premium = True
        db.session.commit()
        flash("🎉 Congratulations! You are now a premium user.", "success")
    else:
        flash("❌ Payment failed or not verified.", "error")

    return redirect("/dashboard")