import random, re
from uuid import uuid4

from bs4 import BeautifulSoup
from flask import render_template

from app.models import Ad
from app.services.superior_ads import (
    get_superior_ads,
    make_ad_tracking_context,
)


def build_article_soup(content):
    """
    Convert saved article content into HTML while preserving paragraphs.
    Supports existing HTML and plain-text articles.
    """
    raw_content = content or ""
    soup = BeautifulSoup(raw_content, "html.parser")

    # If the content already has block-level HTML, preserve it.
    existing_blocks = soup.find_all(
        ["p", "div", "h1", "h2", "h3", "blockquote", "ul", "ol"]
    )

    if existing_blocks:
        return soup

    # Extract text and normalize Windows/Linux line endings.
    text = soup.get_text()
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split on blank lines so each original paragraph remains separate.
    blocks = re.split(r"\n\s*\n+", text.strip())

    result = BeautifulSoup("", "html.parser")

    for block in blocks:
        block = block.strip()

        if not block:
            continue

        paragraph = result.new_tag("p")
        paragraph.string = block
        result.append(paragraph)

    return result

def inject_inpost_content(
    content,
    category=None,
    topic=None,
):
    """
    Insert distinct central Superior Ads after every two
    readable paragraphs, while preserving local post_mid ads.
    """
  
    soup = build_article_soup(content)

    # Identify readable article blocks produced by the custom editor.
    paragraphs = [
        element
        for element in soup.find_all(["p", "div"])
        if element.get_text(" ", strip=True)
        and not element.find(["p", "div"])
    ]

    if not paragraphs:
        return str(soup)

    # Avoid inserting an ad after the final paragraph.
    insertion_points = list(
        range(3, len(paragraphs), 3)
    )

    # --------------------------------------------------
    # CENTRAL SUPERIOR ADS
    # Reuse returned ads when there are fewer campaigns
    # than available insertion points.
    # --------------------------------------------------

    central_ads = []

    if insertion_points:

        try:
            central_ads = get_superior_ads(
                placement="in_content",
                category=category,
                topic=topic,
                limit=len(insertion_points),
            ) or []

        except Exception as exc:
            print(
                f"[ARTICLE ADS] ERROR: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

    else:
        print(
            "[ARTICLE ADS] No insertion points generated.",
            flush=True,
        )

    # Validate returned ads. Campaigns must have an ID,
    # a usable click URL, and at least one media item.
    valid_ads = []
    seen_campaign_ids = set()

    for ad in central_ads:
        if not isinstance(ad, dict):
            continue

        campaign_id = ad.get("campaign_id") or ad.get("id")
        tracking = ad.get("tracking") or {}
        media = ad.get("media") or []

        if not campaign_id:
            continue

        if not tracking.get("click_url") or not media:
            continue

        # Remove duplicate entries in the API response.
        if campaign_id in seen_campaign_ids:
            continue

        seen_campaign_ids.add(campaign_id)
        valid_ads.append(ad)

    # Pair each insertion point with an ad.
    # If only two valid ads are returned, reuse them:
    # A, B, A, B, A, B...
    insertion_ads = []

    if valid_ads:
        for index, paragraph_count in enumerate(insertion_points):
            ad = valid_ads[index % len(valid_ads)]

            insertion_ads.append(
                (paragraph_count, ad)
            )

    else:
        print(
            "[ARTICLE ADS] No valid central ads to insert.",
            flush=True,
        )

    # Insert from the end toward the beginning so existing
    # paragraph references remain valid.
    for paragraph_count, ad in reversed(insertion_ads):
        try:
            tracking_context = make_ad_tracking_context(
                ad,
                publisher="superior-news",
                placement="in_content",
            )
    
            if not tracking_context:
                print(
                    "[ARTICLE ADS] Skipping campaign: "
                    "tracking URLs could not be normalized.",
                    flush=True,
                )
                continue
    
            # Use the normalized ad returned by the tracking helper.
            normalized_ad = dict(ad)
            normalized_ad["tracking"] = {
                **(ad.get("tracking") or {}),
                "impression_url": tracking_context["impression_url"],
                "impression_event_id": tracking_context[
                    "impression_event_id"
                ],
                "click_url": tracking_context["click_url"],
                "click_event_id": tracking_context["click_event_id"],
            }
    
            ad_html = render_template(
                "ads/superiorAdBlock.html",
                ad=normalized_ad,
                ad_instance_id=str(uuid4()),
                impression_event_id=tracking_context[
                    "impression_event_id"
                ],
                click_event_id=tracking_context["click_event_id"],
                publisher=tracking_context["publisher"],
                placement=tracking_context["placement"],
            )
    
            ad_soup = BeautifulSoup(
                ad_html,
                "html.parser",
            )
    
            ad_nodes = list(ad_soup.contents)
    
            if not ad_nodes:
                continue
    
            anchor = paragraphs[paragraph_count - 1]
    
            if not anchor.parent:
                continue
    
            anchor.insert_after(*ad_nodes)
    
        except Exception as exc:
            print(
                f"[ARTICLE ADS] RENDER/INSERT ERROR: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

    # --------------------------------------------------
    # EXISTING LOCAL POST-MID ADS
    # --------------------------------------------------

    try:
        local_ads = Ad.query.filter_by(
            location="post_mid",
            active=True,
        ).all()
    except Exception:
        return str(soup)

    if not local_ads:
        return str(soup)

    article_paragraphs = paragraphs

    # --------------------------------------------------
    # FIRST LOCAL AD
    # --------------------------------------------------

    if len(article_paragraphs) >= 3:
        first_ad = random.choice(local_ads)

        try:
            first_ad_html = render_template(
                "ads/adBlock.html",
                location="post_mid",
                ad=first_ad,
            )

            first_ad_soup = BeautifulSoup(
                first_ad_html,
                "html.parser",
            )

            first_position = min(
                max(
                    2,
                    len(article_paragraphs) // 4,
                ),
                len(article_paragraphs),
            )

            anchor = article_paragraphs[
                first_position - 1
            ]

            if anchor.parent and first_ad_soup.contents:
                anchor.insert_after(
                    *list(first_ad_soup.contents)
                )

        except Exception:
            pass

    # --------------------------------------------------
    # SECOND LOCAL AD FOR LONG ARTICLES
    # --------------------------------------------------

    if len(article_paragraphs) >= 8:
        second_ad = random.choice(local_ads)

        try:
            second_ad_html = render_template(
                "ads/adBlock.html",
                location="post_mid",
                ad=second_ad,
            )

            second_ad_soup = BeautifulSoup(
                second_ad_html,
                "html.parser",
            )

            second_position = min(
                (len(article_paragraphs) * 3) // 4,
                len(article_paragraphs),
            )

            anchor = article_paragraphs[
                second_position - 1
            ]

            if anchor.parent and second_ad_soup.contents:
                anchor.insert_after(
                    *list(second_ad_soup.contents)
                )

        except Exception:
            pass

    final_html = str(soup)
    
    return final_html