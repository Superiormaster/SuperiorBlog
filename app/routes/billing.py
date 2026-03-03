import requests, uuid, hmac, hashlib
from sqlalchemy import func
from flask import (
    Blueprint, request, redirect,
    url_for, flash, current_app, render_template
)
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app.extensions import db, csrf
from app.utils.db_helpers import safe_commit
from app.models import Payment, User


billing_bp = Blueprint("billings", __name__)

# ----------------------------
# PLANS
# ----------------------------
PLANS = {
    "monthly": {
        "amount": 200000,   # ₦2,000
        "duration_days": 30
    },
    "yearly": {
        "amount": 2000000,  # ₦20,000
        "duration_days": 365
    }
}

# ----------------------------
# INIT PAYMENT
# ----------------------------
@billing_bp.route("/paystack/init/<plan>", methods=["POST"])
@login_required
def init_payment(plan):

    if plan not in PLANS:
        flash("Invalid plan selected.", "danger")
        return redirect(url_for("public.pricing"))

    try:
        secret_key = current_app.config["PAYSTACK_SECRET_KEY"]
        base_url = current_app.config["PAYSTACK_BASE_URL"]

        reference = str(uuid.uuid4())
        amount = PLANS[plan]["amount"]

        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json"
        }

        data = {
            "email": current_user.email,
            "amount": amount,
            "reference": reference,
            "callback_url": url_for("billings.payment_success", _external=True)
        }

        response = requests.post(
            f"{base_url}/transaction/initialize",
            json=data,
            headers=headers,
            timeout=20
        ).json()

        if response.get("status"):

            payment = Payment(
                reference=reference,
                email=current_user.email,
                amount=amount,
                plan=plan,
                status="pending"
            )

            db.session.add(payment)
            safe_commit()

            return redirect(response["data"]["authorization_url"])

        flash("Payment initialization failed.", "danger")
        return redirect(url_for("public.pricing"))

    except Exception as e:
        print("Paystack init error:", e)
        flash("Something went wrong. Try again.", "danger")
        return redirect(url_for("public.pricing"))


# ----------------------------
# PAYMENT SUCCESS PAGE
# ----------------------------
@billing_bp.route("/payment/success")
@login_required
def payment_success():

    reference = request.args.get("reference")

    if not reference:
        flash("No payment reference found.", "danger")
        return redirect(url_for("public.pricing"))

    try:
        secret_key = current_app.config["PAYSTACK_SECRET_KEY"]
        base_url = current_app.config["PAYSTACK_BASE_URL"]

        headers = {
            "Authorization": f"Bearer {secret_key}"
        }

        response = requests.get(
            f"{base_url}/transaction/verify/{reference}",
            headers=headers,
            timeout=20
        ).json()

        payment = Payment.query.filter_by(reference=reference).first()

        if not payment:
          flash("Payment record not found.", "danger")
          return redirect(url_for("public.pricing"))

        if (
            response.get("status") and
            response["data"]["status"] == "success" and
            response["data"]["amount"] == payment.amount
        ):

            if payment and payment.status != "success":

                payment.status = "success"

                duration = PLANS[payment.plan]["duration_days"]

                user = User.query.filter_by(email=payment.email).first()
                if user.premium_expires_at and user.premium_expires_at > datetime.utcnow():
                    new_expiry = user.premium_expires_at + timedelta(days=duration)
                else:
                    new_expiry = datetime.utcnow() + timedelta(days=duration)

                user.is_premium = True
                user.premium_expires_at = new_expiry

                safe_commit()
                db.session.refresh(current_user)

            flash("Payment successful! Premium activated.", "success")
            return redirect(url_for("caption.caption_page"))

        flash("Payment verification failed.", "danger")
        return redirect(url_for("public.pricing"))

    except Exception as e:
        print("Verification error:", e)
        flash("Something went wrong verifying payment.", "danger")
        return redirect(url_for("public.pricing"))


@billing_bp.route("/subscription/cancel", methods=["POST"])
@login_required
def cancel_subscription():

    current_user.is_premium = False
    current_user.premium_expires_at = None

    safe_commit()

    flash("Subscription cancelled successfully.", "info")
    return redirect(url_for("user.dashboard"))


# ----------------------------
# WEBHOOK (SECURE)
# ----------------------------
@billing_bp.route("/paystack/webhook", methods=["POST"])
@csrf.exempt
def paystack_webhook():

    secret_key = current_app.config["PAYSTACK_SECRET_KEY"]

    # Verify signature
    signature = request.headers.get("x-paystack-signature")
    computed_hash = hmac.new(
        secret_key.encode("utf-8"),
        request.data,
        hashlib.sha512
    ).hexdigest()

    if signature != computed_hash:
        return "Invalid signature", 400

    payload = request.get_json()
    event = payload.get("event")

    if event == "charge.success":

        data = payload["data"]
        reference = data["reference"]

        payment = Payment.query.filter_by(reference=reference).first()

        if payment and payment.status != "success":

            payment.status = "success"

            user = User.query.filter_by(email=payment.email).first()

            if user:
                duration = PLANS[payment.plan]["duration_days"]

                # Extend if already premium
                if user.premium_expires_at and user.premium_expires_at > datetime.utcnow():
                    new_expiry = user.premium_expires_at + timedelta(days=duration)
                else:
                    new_expiry = datetime.utcnow() + timedelta(days=duration)

                user.is_premium = True
                user.premium_expires_at = new_expiry

            safe_commit()

    return "", 200


@billing_bp.route("/payments")
@login_required
def payment_history():

    payments = Payment.query.filter_by(
        email=current_user.email
    ).order_by(Payment.created_at.desc()).all()

    return render_template(
        "tools/history.html",
        payments=payments
    )


@billing_bp.route("/admin/payments")
@login_required
def admin_payments():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("public.user_login"))

    subquery = (
        db.session.query(
            Payment.email,
            Payment.plan,
            func.max(Payment.created_at).label("latest_date")
        )
        .group_by(Payment.email, Payment.plan)
        .subquery()
    )

    # Join back to payments table to get full payment details
    latest_payments = (
        db.session.query(Payment)
        .join(
            subquery,
            (Payment.email == subquery.c.email) &
            (Payment.plan == subquery.c.plan) &
            (Payment.created_at == subquery.c.latest_date)
        )
        .order_by(Payment.created_at.desc())
        .all()
    )

    users = User.query.all()

    return render_template(
        "admin/payments.html",
        payments=latest_payments,
        users=users
    )


@billing_bp.route("/admin/verify/<reference>", methods=["POST"])
@login_required
def manual_verify(reference):

    payment = Payment.query.filter_by(reference=reference).first()

    if not payment:
        flash("Payment not found.", "danger")
        return redirect(url_for("billings.admin_payments"))

    secret_key = current_app.config["PAYSTACK_SECRET_KEY"]
    base_url = current_app.config["PAYSTACK_BASE_URL"]

    headers = {"Authorization": f"Bearer {secret_key}"}

    response = requests.get(
        f"{base_url}/transaction/verify/{reference}",
        headers=headers
    ).json()

    if response.get("status") and response["data"]["status"] == "success":

        payment.status = "success"

        user = User.query.filter_by(email=payment.email).first()

        if user:
            duration = PLANS[payment.plan]["duration_days"]

            if user.premium_expires_at and user.premium_expires_at > datetime.utcnow():
                new_expiry = user.premium_expires_at + timedelta(days=duration)
            else:
                new_expiry = datetime.utcnow() + timedelta(days=duration)

            user.is_premium = True
            user.premium_expires_at = new_expiry

        safe_commit()
        flash("Payment verified and activated.", "success")
    else:
        flash("Verification failed.", "danger")

    return redirect(url_for("billings.admin_payments"))

@billing_bp.route("/admin/toggle/<reference>", methods=["POST"])
@login_required
def toggle_payment(reference):

    payment = Payment.query.filter_by(reference=reference).first()

    if not payment:
        flash("Payment not found.", "danger")
        return redirect(url_for("billings.admin_payments"))

    payment.status = "success"

    user = User.query.filter_by(email=payment.email).first()

    if user:
        duration = PLANS[payment.plan]["duration_days"]

        user.is_premium = True
        user.premium_expires_at = datetime.utcnow() + timedelta(days=duration)

    safe_commit()
    flash("Payment manually activated.", "success")

    return redirect(url_for("billings.admin_payments"))


# ----------------------------
# AUTO EXPIRY CHECK
# ----------------------------
def check_premium_status(user):

    if user.is_premium and user.premium_expires_at:
        if datetime.utcnow() > user.premium_expires_at:
            user.is_premium = False
            user.premium_expires_at = None
            safe_commit()