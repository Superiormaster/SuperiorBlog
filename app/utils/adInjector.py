import random
from bs4 import BeautifulSoup
from flask import render_template
from app.models import Ad


def inject_inpost_content(content):
    ads = Ad.query.filter_by(location="post_mid", active=True).all()

    if not ads:
        return content

    soup = BeautifulSoup(content, "html.parser")

    # Find readable content blocks
    blocks = [
        block
        for block in soup.find_all(["p", "div"])
        if block.get_text(strip=True)
    ]

    if len(blocks) < 3:
        return content

    total = len(blocks)

    # -------------------------
    # First Ad (25%)
    # -------------------------
    first_ad = random.choice(ads)
    first_ad_html = render_template(
        "ads/adBlock.html",
        location="post_mid",
        ad=first_ad,
    )

    blocks[max(2, total // 4)].insert_after(
        BeautifulSoup(first_ad_html, "html.parser")
    )

    # -------------------------
    # Second Ad (75%)
    # -------------------------
    if total >= 8:
        second_ad = random.choice(ads)

        second_ad_html = render_template(
            "ads/adBlock.html",
            location="post_mid",
            ad=second_ad,
        )

        blocks[(total * 3) // 4].insert_after(
            BeautifulSoup(second_ad_html, "html.parser")
        )

    return str(soup)