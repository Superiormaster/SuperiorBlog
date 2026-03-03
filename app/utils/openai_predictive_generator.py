import random
from app.models import XPost, XPostMetrics

def predictive_engagement_boost(base_score, user):
    """Optional boost for premium users"""
    if not user.is_premium:
        return base_score
    return min(base_score + random.randint(5, 15), 100)