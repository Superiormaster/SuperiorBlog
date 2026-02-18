import random
from app.models import XPost, XPostMetrics

def predictive_best_time(user):
    """
    Suggest the best posting hour (HH:00) for a user based on past X posts.
    Falls back to peak hours if no data exists.
    """
    if not user:
        return random.choice([8, 10, 12, 15, 17, 19, 21])

    posts = XPost.query.filter_by(user_id=user.id).all()
    if not posts:
        return random.choice([8, 10, 12, 15, 17, 19, 21])

    hour_scores = {}
    for post in posts:
        if not post.created_at:
            continue
        metrics = XPostMetrics.query.filter_by(post_id=post.id).first()
        if not metrics:
            continue
        hour = post.created_at.hour
        hour_scores.setdefault(hour, []).append(metrics.engagement_score)

    if not hour_scores:
        return random.choice([8, 10, 12, 15, 17, 19, 21])

    # Compute average per hour
    avg_scores = {h: sum(scores)/len(scores) for h, scores in hour_scores.items()}
    best_hour = max(avg_scores, key=avg_scores.get)

    return f"{best_hour}:00"

def predictive_engagement_boost(base_score, user):
    """Optional boost for premium users"""
    if not user.is_premium:
        return base_score
    return min(base_score + random.randint(5, 15), 100)