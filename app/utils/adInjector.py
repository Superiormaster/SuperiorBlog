import random
from bs4 import BeautifulSoup
from flask import render_template
from app.models import Ad

def inject_inpost_content(content, related_posts=None, section_title="Related Stories"):
    ads = Ad.query.filter_by(location="post_mid", active=True).all()
    # Uncomment after AdSense approval if you want network ads
    # ads = [ad for ad in ads if ad.type != "adsterra"]

    if not ads:
        return content

    soup = BeautifulSoup(content, "html.parser")

    # Find readable blocks
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
    if ads:
        ad = random.choice(ads)
        ad_html = render_template(
            "ads/adBlock.html",
            location="post_mid",
            ad=ad,
        )

        ad_soup = BeautifulSoup(ad_html, "html.parser")

        ad_position = max(2, total // 4)
        blocks[ad_position].insert_after(ad_soup)

    # -------------------------
    # Related Posts (50%)
    # -------------------------
    if related_posts:
        related_html = render_template(
            "partials/inline_related_posts.html",
            related_posts=related_posts,
            section_title=section_title,
        )

        related_soup = BeautifulSoup(related_html, "html.parser")

        middle_position = total // 2
        blocks[middle_position].insert_after(related_soup)

    # -------------------------
    # Second Ad (75%)
    # -------------------------
    if ads and total >= 8:
        ad = random.choice(ads)

        ad_html = render_template(
            "ads/adBlock.html",
            location="post_mid",
            ad=ad,
        )

        ad_soup = BeautifulSoup(ad_html, "html.parser")

        second_position = (total * 3) // 4
        blocks[second_position].insert_after(ad_soup)

    return str(soup)