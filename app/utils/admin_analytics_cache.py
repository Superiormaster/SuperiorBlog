from datetime import datetime, timedelta

from sqlalchemy import func

from app.extensions import db, cache
from app.models import (
    Post,
    User,
    Comment,
    Repost,
    PageView,
    XPost,
)
from app.utils.analytics import (
    analytics_block,
    percentage_growth,
    safe_list,
    active_users_by_day,
)


ANALYTICS_CACHE_TIMEOUT = 60


@cache.memoize(timeout=ANALYTICS_CACHE_TIMEOUT)
def get_admin_analytics(range_days=7):
    """
    Return cached admin analytics data for the selected date range.

    Cache keys are separated by range_days.
    """

    now = datetime.utcnow()
    start = now - timedelta(days=range_days)

    growth_defaults = 0

    # --------------------------------------------------
    # POST AND USER COUNTS
    # --------------------------------------------------

    total_posts, total_posts_growth = analytics_block(
        Post,
        Post.created_at,
        range_days,
    )

    total_registered_users = User.query.count()

    current_users = User.query.filter(
        User.created_at >= start
    ).count()

    previous_users = User.query.filter(
        User.created_at.between(
            now - timedelta(days=range_days * 2),
            start,
        )
    ).count()

    total_registered_users_growth = percentage_growth(
        current_users,
        previous_users,
    )

    total_deleted_accounts = User.query.filter_by(
        is_deleted=True
    ).count()

    total_users = total_registered_users

    # --------------------------------------------------
    # CAPTION COUNTS
    # --------------------------------------------------

    total_caption_users = (
        db.session.query(
            func.count(func.distinct(XPost.user_id))
        ).scalar()
        or 0
    )

    total_caption_generated = XPost.query.count()

    total_avg_posts = round(
        Post.query.count() / total_users,
        2,
    ) if total_users else 0

    total_avg_caption = round(
        total_caption_generated / total_users,
        2,
    ) if total_users else 0

    # --------------------------------------------------
    # PAGE VIEWS AND TIME
    # --------------------------------------------------

    total_time_on_page = db.session.query(
        func.coalesce(
            func.sum(PageView.read_time) / 60.0,
            0,
        )
    ).filter(
        PageView.created_at >= start
    ).scalar() or 0

    total_unique_sessions = db.session.query(
        func.count(func.distinct(PageView.session_id))
    ).filter(
        PageView.created_at >= start
    ).scalar() or 0

    avg_time_per_session = (
        total_time_on_page / total_unique_sessions
        if total_unique_sessions else 0
    )

    total_views = PageView.query.filter(
        PageView.created_at >= start
    ).count()

    # --------------------------------------------------
    # ENGAGEMENT COUNTS
    # --------------------------------------------------

    # Uses the Post.like_count column rather than executing
    # a separate likes.count() query for every post.
    total_likes = db.session.query(
        func.coalesce(func.sum(Post.like_count), 0)
    ).scalar() or 0

    total_replies = Comment.query.count()
    total_repost = Repost.query.count()

    total_impressions = db.session.query(
        func.coalesce(func.sum(Post.impressions), 0)
    ).scalar() or 0

    total_profile_visits = db.session.query(
        func.coalesce(func.sum(User.profile_visits), 0)
    ).scalar() or 0

    total_shares = db.session.query(
        func.coalesce(func.sum(Post.shares), 0)
    ).scalar() or 0

    total_engagements = (
        total_likes
        + total_replies
        + total_shares
        + total_repost
    )

    total_engagement_rate = (
        round(
            total_engagements / total_impressions * 100,
            2,
        )
        if total_impressions else 0
    )

    total_read_time = db.session.query(
        func.coalesce(func.sum(Post.read_time), 0)
    ).scalar() or 0

    # --------------------------------------------------
    # ACTIVE USERS
    # --------------------------------------------------

    dau_labels, dau_values = active_users_by_day(7)

    DAU = User.query.filter(
        User.last_login >= now - timedelta(days=1)
    ).count()

    WAU = User.query.filter(
        User.last_login >= now - timedelta(days=7)
    ).count()

    MAU = User.query.filter(
        User.last_login >= now - timedelta(days=30)
    ).count()

    DAU_prev = User.query.filter(
        User.last_login.between(
            now - timedelta(days=2),
            now - timedelta(days=1),
        )
    ).count()

    WAU_prev = User.query.filter(
        User.last_login.between(
            now - timedelta(days=14),
            now - timedelta(days=7),
        )
    ).count()

    MAU_prev = User.query.filter(
        User.last_login.between(
            now - timedelta(days=60),
            now - timedelta(days=30),
        )
    ).count()

    DAU_growth = percentage_growth(DAU, DAU_prev)
    WAU_growth = percentage_growth(WAU, WAU_prev)
    MAU_growth = percentage_growth(MAU, MAU_prev)

    total_content_creators = db.session.query(
        func.count(func.distinct(Post.user_id))
    ).scalar() or 0

    total_logged_in_users = User.query.filter(
        User.last_login.isnot(None)
    ).count()

    active_last_7_days = User.query.filter(
        User.last_login >= now - timedelta(days=7)
    ).count()

    # --------------------------------------------------
    # POST CHARTS
    # --------------------------------------------------

    post_counts = db.session.query(
        func.date(Post.created_at),
        func.count(Post.id),
    ).filter(
        Post.created_at >= start
    ).group_by(
        func.date(Post.created_at)
    ).order_by(
        func.date(Post.created_at)
    ).all()

    labels = [str(row[0]) for row in post_counts]
    post_data = [row[1] for row in post_counts]

    like_counts = db.session.query(
        func.date(Post.created_at),
        func.coalesce(func.sum(Post.like_count), 0),
    ).filter(
        Post.created_at >= start
    ).group_by(
        func.date(Post.created_at)
    ).order_by(
        func.date(Post.created_at)
    ).all()

    likes_data = [row[1] for row in like_counts]

    view_counts = db.session.query(
        func.date(PageView.created_at),
        func.count(PageView.id),
    ).filter(
        PageView.created_at >= start
    ).group_by(
        func.date(PageView.created_at)
    ).order_by(
        func.date(PageView.created_at)
    ).all()

    views_data = [row[1] for row in view_counts]

    # --------------------------------------------------
    # CAPTION CHARTS
    # --------------------------------------------------

    xpost_counts = db.session.query(
        func.date(XPost.created_at),
        func.count(XPost.id),
    ).filter(
        XPost.created_at >= start
    ).group_by(
        func.date(XPost.created_at)
    ).order_by(
        func.date(XPost.created_at)
    ).all()

    xpost_labels = [str(row[0]) for row in xpost_counts]
    xpost_data = [row[1] for row in xpost_counts]

    avg_caption_length = db.session.query(
        func.avg(func.length(XPost.text))
    ).scalar() or 0

    short_posts = XPost.query.filter(
        func.length(XPost.text) <= 120
    ).count()

    medium_posts = XPost.query.filter(
        func.length(XPost.text).between(121, 200)
    ).count()

    long_posts = XPost.query.filter(
        func.length(XPost.text) > 200
    ).count()

    avg_confidence = db.session.query(
        func.avg(XPost.confidence_score)
    ).scalar() or 0

    best_times = db.session.query(
        XPost.best_post_time,
        func.count(XPost.id),
    ).group_by(
        XPost.best_post_time
    ).order_by(
        func.count(XPost.id).desc()
    ).limit(5).all()

    best_time_labels = [str(row[0]) for row in best_times]
    best_time_data = [row[1] for row in best_times]

    xposts = XPost.query.all()

    total_predicted = 0

    for xpost in xposts:
        if xpost.predicted_engagement:
            total_predicted += sum(
                xpost.predicted_engagement.values()
            )

    avg_predicted_engagement = (
        total_predicted / len(xposts)
        if xposts else 0
    )

    top_x_creators = db.session.query(
        User.username,
        func.count(XPost.id),
    ).join(
        XPost,
        XPost.user_id == User.id,
    ).group_by(
        User.username
    ).order_by(
        func.count(XPost.id).desc()
    ).limit(5).all()

    top_x_creators_display = [
        {"username": username, "posts": count}
        for username, count in top_x_creators
    ]

    caption_counts = db.session.query(
        func.date(XPost.created_at),
        func.count(XPost.id),
    ).filter(
        XPost.created_at >= start
    ).group_by(
        func.date(XPost.created_at)
    ).order_by(
        func.date(XPost.created_at)
    ).all()

    caption_counts_display = [
        {"date": str(row[0]), "count": row[1]}
        for row in caption_counts
    ]

    return {
        "total_views": total_views,
        "total_read_time": total_read_time,
        "total_active_users": total_logged_in_users,
        "total_time_on_page": total_time_on_page,
        "avg_time_per_session": round(avg_time_per_session, 2),
        "DAU": DAU,
        "WAU": WAU,
        "MAU": MAU,
        "DAU_growth": DAU_growth,
        "WAU_growth": WAU_growth,
        "MAU_growth": MAU_growth,
        "dau_labels": dau_labels,
        "dau_values": dau_values,
        "total_content_creators": total_content_creators,
        "active_last_7_days": active_last_7_days,
        "total_registered_users": total_registered_users,
        "total_registered_users_growth": total_registered_users_growth,
        "total_likes": total_likes,
        "total_replies": total_replies,
        "total_posts": total_posts,
        "total_posts_growth": total_posts_growth,
        "total_deleted_accounts": total_deleted_accounts,
        "total_caption_users": total_caption_users,
        "total_caption_generated": total_caption_generated,
        "total_avg_caption": total_avg_caption,
        "total_avg_posts": total_avg_posts,
        "unique_visitors": total_unique_sessions,
        "avg_caption_length": round(avg_caption_length, 2),
        "short_posts": short_posts,
        "medium_posts": medium_posts,
        "long_posts": long_posts,
        "avg_confidence": round(avg_confidence, 2),
        "top_x_creators_display": top_x_creators_display,
        "caption_counts_display": caption_counts_display,
        "best_time_labels": best_time_labels,
        "best_time_data": best_time_data,
        "avg_predicted_engagement": round(avg_predicted_engagement, 2),
        "total_repost": total_repost,
        "total_impressions": total_impressions,
        "views_data": safe_list(views_data),
        "likes_data": safe_list(likes_data),
        "labels": labels,
        "post_data": post_data,
        "xpost_labels": xpost_labels,
        "xpost_data": xpost_data,
        "total_profile_visits": total_profile_visits,
        "total_shares": total_shares,
        "total_engagements": total_engagements,
        "total_engagement_rate": total_engagement_rate,
        "growth_defaults": growth_defaults,
    }