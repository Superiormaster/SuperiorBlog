from bs4 import BeautifulSoup
from flask import render_template
from app.models import Ad

def inject_inpost_ads(content):
    ad = Ad.query.filter_by(location="in_post", active=True).first()
    if not ad:
        return content

    soup = BeautifulSoup(content, "html.parser")
    paragraphs = soup.find_all("p")

    # Only inject if there are 2 or more paragraphs
    if len(paragraphs) > 2:
        ad_html = render_template("ads/adBlock.html", location="post_mid")
        ad_soup = BeautifulSoup(ad_html, "html.parser")
        paragraphs[1].insert_after(ad_soup)  # insert after 2nd paragraph

    return str(soup)