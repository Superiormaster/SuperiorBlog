from bs4 import BeautifulSoup
from flask import render_template
from app.models import Ad

def inject_inpost_ads(content):
  ad = Ad.query.filter_by(location="post_mid", active=True).first()
  if not ad:
      return content

  soup = BeautifulSoup(content, "html.parser")

  blocks = [b for b in soup.find_all(["p", "div"]) if b.get_text(strip=True)]

  # Only inject if there are 2 or more blocks
  if len(blocks) > 2:
      ad_html = render_template("ads/adBlock.html", location="post_mid")
      ad_soup = BeautifulSoup(ad_html, "html.parser")
      blocks[1].insert_after(ad_soup)  # insert after 2nd block

  return str(soup)