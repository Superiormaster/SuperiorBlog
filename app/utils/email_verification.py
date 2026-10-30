from flask import current_app, render_template, url_for
from app.utils.email import send_email


def send_verification_email(user):

    token = user.generate_verification_token()

    verification_url = url_for(
        "public.verify_email",
        token=token,
        _external=True
    )

    html_content = render_template(
        "emails/verify_email.html",
        verification_url=verification_url,
        expiry_hours=24
    )

    result = send_email(
        to=user.email,
        subject="Verify Your Superior News Account",
        html_content=html_content,
        text_content=(
            "Welcome to Superior News. "
            "Verify your email using this link: "
            f"{verification_url}"
        )
    )

    if not isinstance(result, dict):
        current_app.logger.error(
            "Unexpected email response for user %s", user.id
        )
        return False

    if not result.get("success"):
        current_app.logger.error(
            "Verification email failed for user %s: %s",
            user.id,
            result.get("error")
        )
        return False

    return True