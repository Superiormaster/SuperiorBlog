from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.utils.db_helpers import safe_commit
from app.models import Comment

comments_bp = Blueprint("comments", __name__)

@comments_bp.route("/comments/create", methods=["POST"])
@login_required
def create_comment():
    post_id = request.form.get("post_id")
    content = request.form.get("content", "").strip()

    if not content:
        return jsonify({"error": "Comment cannot be empty"}), 400

    comment = Comment(
        post_id=post_id,
        user_id=current_user.id,
        content=content
    )

    db.session.add(comment)
    db.session.commit()

    return jsonify({
        "success": True,
        "comment_id": comment.id
    })

@comments_bp.route("/comments/reply/<int:comment_id>", methods=["POST"])
@login_required
def reply_to_comment(comment_id):
    parent = Comment.query.get_or_404(comment_id)
    content = request.form.get("content", "").strip()

    if not content:
        return jsonify({"error": "Reply cannot be empty"}), 400

    reply = Comment(
        post_id=parent.post_id,
        user_id=current_user.id,
        parent_id=parent.id,
        content=content
    )

    parent.replies_count += 1

    db.session.add(reply)
    db.session.commit()

    return jsonify({
        "success": True,
        "reply_id": reply.id
    })

@comments_bp.route("/comments/<int:post_id>")
def fetch_comments(post_id):
    limit = int(request.args.get("limit", 10))
    offset = int(request.args.get("offset", 0))

    comments = (
        Comment.query
        .filter(
            Comment.post_id == post_id,
            Comment.parent_id.is_(None),
            Comment.is_deleted.is_(False)
        )
        .order_by(Comment.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return jsonify([
        {
            "id": c.id,
            "content": c.content,
            "user": c.user.username,
            "created_at": c.created_at.isoformat(),
            "replies_count": c.replies_count
        }
        for c in comments
    ])

@comments_bp.route("/comments/replies/<int:comment_id>")
def fetch_replies(comment_id):
    limit = int(request.args.get("limit", 2))
    offset = int(request.args.get("offset", 0))

    replies = (
        Comment.query
        .filter(
            Comment.parent_id == comment_id,
            Comment.is_deleted.is_(False)
        )
        .order_by(Comment.created_at.asc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return jsonify([
        {
            "id": r.id,
            "content": r.content,
            "user": r.user.username,
            "created_at": r.created_at.isoformat()
        }
        for r in replies
    ])

@comments_bp.route("/comments/delete/<int:comment_id>", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    if comment.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    comment.is_deleted = True
    comment.content = "[deleted]"

    if comment.parent_id:
        parent = Comment.query.get(comment.parent_id)
        if parent and parent.replies_count > 0:
            parent.replies_count -= 1

    db.session.commit()

    return jsonify({"success": True})

@comments_bp.route("/comments/react/<int:comment_id>", methods=["POST"])
@login_required
def react_to_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    reaction_type = request.form.get("reaction")

    if reaction_type not in ["like", "love", "haha", "wow", "sad", "angry"]:
        return jsonify({"error": "Invalid reaction"}), 400

    # check if user already reacted
    existing = CommentReaction.query.filter_by(comment_id=comment.id, user_id=current_user.id).first()

    if existing:
        if existing.reaction == reaction_type:
            # Remove reaction if same type (toggle off)
            db.session.delete(existing)
            comment.reactions_count = max(comment.reactions_count - 1, 0)
        else:
            # Change reaction type
            existing.reaction = reaction_type
    else:
        # Add new reaction
        new_reaction = CommentReaction(comment_id=comment.id, user_id=current_user.id, reaction=reaction_type)
        db.session.add(new_reaction)
        comment.reactions_count += 1

    db.session.commit()

    # Return updated reactions count for frontend
    counts = {}
    for r_type in ["like", "love", "haha", "wow", "sad", "angry"]:
        counts[r_type] = CommentReaction.query.filter_by(comment_id=comment.id, reaction=r_type).count()

    return jsonify({"success": True, "counts": counts})