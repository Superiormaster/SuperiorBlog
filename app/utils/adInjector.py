from flask import render_template
from app.models import Ad

def inject_inpost_ads(content):
    ad = Ad.query.filter_by(location="in_post", active=True).first()

    if not ad:
        return content

    paragraphs = content.split("</p>")

    if len(paragraphs) > 2:
        ad_html = render_template("ads/adBlock.html", location="in_post")
        paragraphs.insert(2, ad_html)

    return "</p>".join(paragraphs)