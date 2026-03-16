import random
from bs4 import BeautifulSoup
from flask import render_template
from app.models import Ad

def inject_inpost_ads(content):
    ads = Ad.query.filter_by(location="post_mid", active=True).all()
    # Uncomment after AdSense approval if you want network ads
    # ads = [ad for ad in ads if ad.type != "adsterra"]

    if not ads:
        return content

    soup = BeautifulSoup(content, "html.parser")
    blocks = [b for b in soup.find_all(["p", "div"]) if b.get_text(strip=True)]

    if len(blocks) < 3:
        return content  # not enough blocks to insert an ad

    # Pick one ad and one position
    ad = random.choice(ads)
    pos = min(3, len(blocks) - 1)  # 3rd paragraph or last if fewer

    ad_html = render_template("ads/adBlock.html", location="post_mid", ad=ad)
    ad_soup = BeautifulSoup(ad_html, "html.parser")
    blocks[pos].insert_after(ad_soup)

    return str(soup)