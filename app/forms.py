from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, BooleanField, FileField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class LoginForm(FlaskForm):
    identifier = StringField("Username or Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class PostForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    content = TextAreaField("Content", validators=[DataRequired()])
    category = SelectField("Category", choices=[], coerce=int, validators=[DataRequired()])
    labels = SelectMultipleField("Labels", choices=[], coerce=int)
    image = FileField("Featured Image")
    is_published = BooleanField("Publish")
    submit = SubmitField("Create Post")

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Current Password",
        validators=[DataRequired(message="Current password is required")]
    )
    new_password = PasswordField(
        "New Password",
        validators=[DataRequired(message="New password is required"), Length(min=6)]
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(message="Please confirm new password"),
            EqualTo("new_password", message="Passwords must match")
        ]
    )
    submit = SubmitField("Change Password")

class ContactForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=50)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=100)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField("Send Message")