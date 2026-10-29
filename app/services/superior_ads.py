import logging
from urllib.parse import (
    urljoin,
    urlparse,
    urlunparse,
    parse_qsl,
    urlencode,
)
from uuid import uuid4

import requests
from flask import current_app


logger = logging.getLogger(__name__)


SUPPORTED_MEDIA_TYPES = {
    "image",
    "gif",
    "video",
}


def ad_log(message):
    """Write Superior Ads diagnostics to the application log."""
    message = f"[SUPERIOR ADS DEBUG] {message}"
    logger.info(message)

    if current_app.debug:
        print(message, flush=True)


def normalize_tracking_url(url):
    """
    Normalize tracking URLs from the central Superior Ads API.

    HTTPS is required in production. HTTP is allowed only for
    localhost during Flask debug mode.
    """
    if not isinstance(url, str) or not url.strip():
        return None

    base_url = (
        current_app.config.get("SUPERIOR_ADS_PUBLIC_URL")
        or current_app.config.get("SUPERIOR_ADS_BASE_URL")
        or ""
    ).strip().rstrip("/")

    if not base_url:
        return None

    normalized = urljoin(
        f"{base_url}/",
        url.strip(),
    )

    parsed = urlparse(normalized)

    if (
        parsed.scheme not in {"https", "http"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        return None

    if parsed.scheme != "https":
        local_development = (
            current_app.debug
            and parsed.hostname.lower() in {
                "localhost",
                "127.0.0.1",
            }
        )

        if not local_development:
            return None

    return normalized

def build_click_url(
    click_url,
    *,
    event_id,
    publisher,
    placement,
):
    """
    Safely append tracking parameters to the central click URL.

    Preserves unrelated existing query parameters and replaces
    existing event_id, publisher, and placement parameters.
    """
    normalized_url = normalize_tracking_url(click_url)

    if not normalized_url:
        return None

    parsed = urlparse(normalized_url)

    tracking_keys = {
        "event_id",
        "publisher",
        "placement",
    }

    query = [
        (key, value)
        for key, value in parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
        if key not in tracking_keys
    ]

    query.extend([
        ("event_id", str(event_id)),
        ("publisher", publisher),
        ("placement", placement),
    ])

    return urlunparse(
        parsed._replace(
            query=urlencode(query),
        )
    )


def make_ad_tracking_context(
    ad,
    *,
    publisher="superior-news",
    placement,
):
    """
    Create fresh UUIDs and a safe click URL for one rendered ad.

    Call this separately for each ad instance.
    """
    if not isinstance(ad, dict):
        return None

    tracking = ad.get("tracking") or {}

    impression_url = normalize_tracking_url(
        tracking.get("impression_url")
    )

    impression_event_id = str(uuid4())
    click_event_id = str(uuid4())

    click_url = build_click_url(
        tracking.get("click_url"),
        event_id=click_event_id,
        publisher=publisher,
        placement=placement,
    )

    if not impression_url or not click_url:
        return None

    return {
        "ad": ad,
        "impression_url": impression_url,
        "impression_event_id": impression_event_id,
        "click_event_id": click_event_id,
        "click_url": click_url,
        "publisher": publisher,
        "placement": placement,
    }

def get_superior_ads(
    placement="in_content",
    category=None,
    topic=None,
    limit=5,
):
    """
    Retrieve advertisements from the central Superior Ads API.

    Supports both response formats:

    Legacy:
        {"success": True, "ads": [...]}

    Current:
        {
            "success": True,
            "ads": {
                "ads": [...],
                "total_ads": 4,
                "pricing": {...}
            }
        }

    Returns a list of validated ads, preserving compatibility
    with existing callers.
    """

    ad_log("get_superior_ads() called.")

    if not current_app.config.get("SUPERIOR_ADS_ENABLED", False):
        ad_log("Integration disabled.")
        return []

    base_url = (
        current_app.config.get("SUPERIOR_ADS_BASE_URL") or ""
    ).strip().rstrip("/")

    if not base_url:
        ad_log("SUPERIOR_ADS_BASE_URL is not configured.")
        return []

    if not isinstance(placement, str) or not placement.strip():
        ad_log("Invalid placement.")
        return []

    placement = placement.strip().lower()

    try:
        limit = max(0, min(int(limit), 20))
    except (TypeError, ValueError):
        limit = 5

    if limit == 0:
        return []

    try:
        timeout = float(
            current_app.config.get("SUPERIOR_ADS_TIMEOUT", 3)
        )

        if timeout <= 0:
            timeout = 3

    except (TypeError, ValueError):
        timeout = 3

    params = {
        "publisher": "superior-news",
        "placement": placement,
        "limit": limit,
    }

    if category:
        params["category"] = str(category)

    if topic:
        params["topic"] = str(topic)

    endpoint = f"{base_url}/api/advertising/serve"

    ad_log(
        f"Requesting placement={placement!r}, "
        f"limit={limit}, category={category!r}, topic={topic!r}"
    )

    try:
        response = requests.get(
            endpoint,
            params=params,
            timeout=timeout,
        )

        ad_log(f"API HTTP status: {response.status_code}")

        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            ad_log("Invalid API response: expected a JSON object.")
            return []

        if not payload.get("success"):
            ad_log(
                f"API returned success=False: "
                f"{payload.get('error')!r}"
            )
            return []

        # --------------------------------------------------
        # Normalize legacy and current response structures.
        # --------------------------------------------------

        ads_container = payload.get("ads")
        pricing = {}
        reported_total_ads = None

        if isinstance(ads_container, dict):
            # Current response:
            # payload["ads"]["ads"] contains the list.
            ads = ads_container.get("ads")

            pricing = ads_container.get("pricing") or {}

            reported_total_ads = ads_container.get("total_ads")

        elif isinstance(ads_container, list):
            # Legacy response:
            # payload["ads"] is directly a list.
            ads = ads_container

            pricing = payload.get("pricing") or {}

            reported_total_ads = payload.get("total_ads")

        elif ads_container is None:
            # Backward compatibility with a single-ad response.
            single_ad = payload.get("ad")

            ads = (
                [single_ad]
                if isinstance(single_ad, dict)
                else []
            )

            pricing = payload.get("pricing") or {}

        else:
            ad_log(
                "Invalid API response: "
                "'ads' must be a list or an object containing an ads list."
            )
            return []

        if not isinstance(ads, list):
            ad_log("Invalid API response: nested ads must be a list.")
            return []

        if not isinstance(pricing, dict):
            pricing = {}

        valid_ads = []
        seen_campaign_ids = set()

        for ad in ads:
            if not isinstance(ad, dict):
                continue

            campaign_id = ad.get("campaign_id") or ad.get("id")

            if campaign_id is None or str(campaign_id).strip() == "":
                continue

            campaign_key = str(campaign_id)

            if campaign_key in seen_campaign_ids:
                continue

            tracking = ad.get("tracking")

            if not isinstance(tracking, dict):
                continue

            click_url = normalize_tracking_url(
                tracking.get("click_url")
            )

            impression_url = normalize_tracking_url(
                tracking.get("impression_url")
            )

            if not click_url or not impression_url:
                ad_log(
                    f"Campaign {campaign_key} rejected: "
                    "invalid tracking URLs."
                )
                continue

            media_assets = ad.get("media")

            if not isinstance(media_assets, list):
                media_assets = []

            valid_media = []

            for media in media_assets:
                if not isinstance(media, dict):
                    continue

                media_url = media.get("url")
                media_type = media.get("media_type")

                if (
                    not isinstance(media_url, str)
                    or not media_url.strip()
                    or media_type not in SUPPORTED_MEDIA_TYPES
                ):
                    continue

                valid_media.append(dict(media))

            normalized_ad = dict(ad)

            normalized_ad["campaign_id"] = campaign_id

            normalized_ad["tracking"] = {
                **tracking,
                "click_url": click_url,
                "impression_url": impression_url,
            }

            normalized_ad["media"] = valid_media

            seen_campaign_ids.add(campaign_key)
            valid_ads.append(normalized_ad)

            if len(valid_ads) >= limit:
                break

        # --------------------------------------------------
        # Expose the summary for existing application callers.
        # --------------------------------------------------

        get_superior_ads.last_summary = {
            "publisher": (
                payload.get("publisher")
                or "superior-news"
            ),
            "placement": (
                payload.get("placement")
                or placement
            ),
            "category": payload.get("category"),
            "topic": payload.get("topic"),
            "requested_limit": limit,
            "reported_total_ads": reported_total_ads,
            "returned_ads": len(valid_ads),
            "pricing": pricing,
        }

        ad_log(
            f"Placement {placement!r}: "
            f"{len(valid_ads)} valid ads returned; "
            f"pricing={pricing.get('total')!r} "
            f"{pricing.get('currency', 'NGN')}."
        )

        return valid_ads

    except requests.Timeout:
        logger.warning(
            "Superior Ads API timed out after %s seconds.",
            timeout,
        )
        return []

    except requests.ConnectionError:
        logger.warning(
            "Superior Ads API connection failed: %s",
            endpoint,
        )
        return []

    except requests.HTTPError:
        logger.exception("Superior Ads API returned an HTTP error.")
        return []

    except requests.RequestException:
        logger.exception("Superior Ads API request failed.")
        return []

    except ValueError:
        logger.exception(
            "Superior Ads API returned invalid JSON."
        )
        return []

    except Exception:
        logger.exception(
            "Unexpected error while retrieving Superior Ads."
        )
        return []


def get_superior_ad(
    placement="in_content",
    category=None,
    topic=None,
):
    """Return one ad for a placement."""
    ads = get_superior_ads(
        placement=placement,
        category=category,
        topic=topic,
        limit=1,
    )

    return ads[0] if ads else None