from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify, flash, make_response
from app.models import Post, Comment, Like, Subscriber, ContactMessage, Category, AppSettings, Tag, post_tags
from markdown import markdown
import os
import traceback
from app.forms import ContactForm
from app.utils.email_helper import send_mailgun_email
from app.extensions import db, cache, csrf
from sqlalchemy import func

public_bp = Blueprint(
    "public",
    __name__, 
    url_prefix="/public",
    template_folder="../templates/public"
)

@public_bp.route("/")
def index():
    posts = (
        Post.query
        .filter_by(is_published=True)
        .order_by(Post.created_at.desc())
        .all()
    )
    
    trending_posts = (
        Post.query
        .outerjoin(Comment)
        .outerjoin(Like)
        .group_by(Post.id)
        .order_by(
            (func.count(Comment.id) + func.count(Like.id)).desc()
        )
        .limit(5)
        .all()
    )
    
    popular_tags = (
        Tag.query
        .join(post_tags)
        .join(Post)
        .filter(Post.is_published == True)
        .group_by(Tag.id)
        .order_by(func.count(Post.id).desc())
        .limit(10)
        .all()
    )
    
    return render_template("homepage.html", posts=posts, trending_posts=trending_posts, popular_tags=popular_tags, Post=Post)

@public_bp.route("/post/<slug>", endpoint='post_detail')
def post_detail(slug):
    post = Post.query.filter_by(slug=slug, is_published=True).first_or_404()
    # Convert Markdown to HTML
    content_html = markdown(post.content or "", extensions=['fenced_code', 'codehilite'])
    
    latest_posts = (
        Post.query
        .filter_by(is_published=True)
        .order_by(Post.created_at.desc())
        .limit(5)
        .all()
    )
    
    related_posts = []
    if post.category_id:
      related_posts = (
          Post.query
          .filter(
              Post.category_id == post.category_id,
              Post.id != post.id,
              Post.is_published == True
          )
          .order_by(Post.created_at.desc())
          .limit(5)
          .all()
      )
    
    post.views = (post.views or 0) + 1
    db.session.commit()

    return render_template("post.html", post=post, content_html=content_html, latest_posts=latest_posts, related_posts=related_posts)

@public_bp.route("/search")
@cache.cached(timeout=300)
def search():
    query = request.args.get("q", "")
    results = []

    if query:
        results = Post.query.filter(
            Post.is_published == True,
            Post.title.ilike(f"%{query}%") |
            Post.content.ilike(f"%{query}%")
        ).order_by(Post.created_at.desc()).all()

    return render_template("search.html", query=query, results=results)

@public_bp.route("/load-more")
@cache.cached(timeout=300)
def load_more():
    page = request.args.get("page", 1, type=int)

    pagination = (
        Post.query
        .filter_by(is_published=True)
        .order_by(Post.created_at.desc())
        .paginate(page=page, per_page=5, error_out=False)
    )

    # ✅ STOP when no posts
    if not pagination.items:
        return jsonify({
            "html": "",
            "has_more": False
        })

    html = render_template(
        "post_cards.html",
        posts=pagination.items
    )

    return jsonify({
        "html": html,
        "has_more": pagination.has_next
    })

@public_bp.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email")

    if not email:
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("public.index"))

    existing = Subscriber.query.filter_by(email=email).first()
    if existing:
        flash("You are already subscribed.", "info")
        return redirect(url_for("public.index"))

    subscriber = Subscriber(email=email)
    db.session.add(subscriber)
    db.session.commit()

    flash("Thanks for subscribing 🎉", "success")
    return redirect(url_for("public.index"))

@public_bp.route("/tag/<string:slug>")
def tag(slug):
    tag = Tag.query.filter_by(slug=slug).first_or_404()

    posts = Post.query.filter(
        Post.tags.contains(tag),
        Post.is_published == True
    ).order_by(Post.created_at.desc()).all()

    return render_template("tag.html", tag=tag, posts=posts)

@public_bp.route("/category/<string:slug>")
@cache.cached(timeout=300)
def category(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()

    posts = (
        Post.query
        .filter_by(category_id=category.id, is_published=True)
        .order_by(Post.created_at.desc())
        .all()
    )

    trending_posts = (
        Post.query
        .filter_by(category_id=category.id, is_published=True)
        .order_by(Post.views.desc())
        .limit(5)
        .all()
    )

    category.views += 1
    db.session.commit()

    return render_template(
        "category.html",
        category=category,
        posts=posts,
        trending_posts=trending_posts
    )

@public_bp.route("/post/<slug>/comment", methods=["POST"])
def add_comment(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()

    author = request.form.get("author", "Anonymous")
    content = request.form.get("content", "").strip()

    if not content:
        return jsonify({"error": "Comment cannot be empty"}), 400

    comment = Comment(author=author, content=content, post_id=post.id)
    db.session.add(comment)
    db.session.commit()

    # Return JSON for AJAX
    return jsonify({
        "author": author,
        "content": content,
        "created_at": comment.created_at.strftime('%b %d, %Y %H:%M')
    })

@csrf.exempt
@public_bp.route("/post/<int:id>/like", methods=["POST"])
def like_post(id):
    post = Post.query.get_or_404(id)

    # Create anonymous session ID
    if "sid" not in session:
        session["sid"] = os.urandom(16).hex()

    # Check if already liked
    existing = Like.query.filter_by(
        post_id=id,
        session_id=session["sid"]
    ).first()

    if existing:
        return jsonify({
            "liked": False,
            "count": Like.query.filter_by(post_id=id).count()
        })

    # Add like
    like = Like(post_id=id, session_id=session["sid"])
    db.session.add(like)
    db.session.commit()

    count = Like.query.filter_by(post_id=id).count()

    return jsonify({
        "liked": True,
        "count": count
    })

# ----- CONTACT US -----
@public_bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        message = form.message.data

        if not email or not message:
            flash("Email and message are required.", "danger")
            return redirect(url_for("public.contact"))

        # Save to DB
        msg = ContactMessage(name=name, email=email, message=message)
        db.session.add(msg)
        db.session.commit()

        # Send email using Mailgun helper
        if send_mailgun_email(
            subject=f"New Contact Message from {name}",
            text=f"Name: {name}\nEmail: {email}\nMessage:\n{message}"
        ):
            flash("Message sent successfully!", "success")
        else:
            traceback.print_exc()
            flash("Message saved, but email failed.", "warning")

        return redirect(url_for("public.contact"))

    return render_template("contact.html", form=form)

# ----- PRIVACY -----
@public_bp.route("/privacy")
@cache.cached(timeout=300)
def privacy():
    settings = AppSettings.query.first()
    return render_template("privacy.html", settings=settings)

@public_bp.route("/terms")
@cache.cached(timeout=300)
def terms():
    settings = AppSettings.query.first()
    return render_template("terms.html", settings=settings)

# Sitemap for Google News
@public_bp.route("/sitemap.xml")
@cache.cached(timeout=300)
def sitemap():
    pages = []
    ten_days_ago = datetime.datetime.now() - datetime.timedelta(days=10)

    # Homepage & categories
    pages.append({"loc": url_for("public.index", _external=True), "lastmod": datetime.datetime.now()})
    for category in Category.query.all():
        pages.append({"loc": url_for("public.category", slug=category.slug, _external=True),
                      "lastmod": datetime.datetime.now()})

    # Posts
    posts = Post.query.filter(Post.is_published==True, Post.created_at >= ten_days_ago).all()
    for post in posts:
        pages.append({"loc": url_for("public.post_detail", slug=post.slug, _external=True),
                      "lastmod": post.updated_at})

    sitemap_xml = render_template("sitemap.xml", pages=pages)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    return response