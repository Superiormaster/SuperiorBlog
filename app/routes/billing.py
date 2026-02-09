import requests
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db, csrf

billing_bp = Blueprint('billings', __name__)

# ----------------------------
# Initialize Payment
# ----------------------------
@billing_bp.route("/paystack/init", methods=["POST"])
@csrf.exempt
@login_required
def init_payment():
    """
    Initialize a Paystack payment for the current user.
    Accepts POST parameter 'amount' (in kobo, e.g., 200000 = ₦2,000)
    """
    try:
        plan_amount = int(request.form.get("amount", 200000))  # Default ₦2,000
        headers = {
            "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "email": current_user.email,
            "amount": plan_amount,
            "callback_url": url_for("billings.verify_payment", _external=True)
        }

        r = requests.post(
            "https://api.paystack.co/transaction/initialize",
            json=data,
            headers=headers,
            timeout=20
        )
        res = r.json()

        if res.get("status"):
            # Redirect user to Paystack payment page
            return redirect(res["data"]["authorization_url"])
        else:
            flash("⚠️ Payment initialization failed. Please try again.", "error")
            return redirect(url_for("pricing"))

    except Exception as e:
        print("Paystack init error:", e)
        flash("⚠️ Payment initialization failed. Please try again.", "error")
        return redirect(url_for("public.pricing"))

# ----------------------------
# Verify Payment
# ----------------------------
@billing_bp.route("/paystack/verify/<ref>")
@login_required
@csrf.exempt
def verify_payment(ref):
    """
    Verify a Paystack payment using the transaction reference.
    Marks the user as premium if successful and redirects to the caption lab.
    """
    try:
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
        r = requests.get(
            f"https://api.paystack.co/transaction/verify/{ref}",
            headers=headers,
            timeout=20
        ).json()

        if r.get("status") and r["data"]["status"] == "success":
            current_user.is_premium = True
            db.session.commit()
            flash("🎉 Congratulations! You are now a premium user.", "success")
            return redirect(url_for("public.caption.lab"))  # caption generator page
        else:
            flash("❌ Payment failed or could not be verified.", "error")
            return redirect(url_for("public.pricing"))

    except Exception as e:
        print("Payment verification error:", e)
        flash("❌ Payment verification failed. Please try again.", "error")
        return redirect(url_for("public.pricing"))