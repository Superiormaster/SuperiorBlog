from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, BooleanField, FileField, SelectMultipleField, DateTimeField, MultipleFileField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp, ValidationError, URL, Length
from flask_wtf.file import FileAllowed, FileField

def validate_full_name(form, field):
    if field.data:
        if len(field.data.strip().split()) < 2:
            raise ValidationError("Please enter your first and last name.")

class LoginForm(FlaskForm):
    identifier = StringField("Username or Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class PostForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(message="Title is required")])
    tribe_url = StringField(
        "Tribe Conversation URL",
        validators=[
            Optional(),
            URL(),
            Length(max=500)
        ]
    )

    tribe_title = StringField(
        "Tribe Conversation Title",
        validators=[
            Optional(),
            Length(max=150)
        ]
    )

    tribe_description = TextAreaField(
        "Tribe Conversation Description",
        validators=[
            Optional(),
            Length(max=500)
        ]
    )

    tribe_button_text = StringField(
        "Tribe Button Text",
        validators=[
            Optional(),
            Length(max=100)
        ]
    )
    category = SelectField("Category", choices=[], coerce=int, validators=[DataRequired()])
    labels = SelectMultipleField("Labels", choices=[], coerce=int)
    scheduled_at = DateTimeField(
        'Schedule',
        format="%Y-%m-%dT%H:%M",
        validators=[Optional()]
    )
    content = TextAreaField("Content", validators=[DataRequired()])

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

class UserRegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Please confirm password"),
            EqualTo("password", message="Passwords must match")
        ]
    )
    submit = SubmitField("Register")

class ForgotPasswordForm(FlaskForm):
    email = StringField("Email",
        validators=[
            DataRequired(message="Please enter your email"),
            Email(message="Please enter a valid email address")
        ])
    submit = SubmitField("Send Reset Link")

class ResetPasswordForm(FlaskForm):
    password = PasswordField("New Password", validators=[DataRequired()])
    confirm_password = PasswordField("Confirm Password",
        validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Reset Password")

class SubscribeForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Enter a valid email address."),
            Length(max=120)
        ]
    )
    submit = SubmitField("Subscribe")

class UserLoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Login")

class ProfileForm(FlaskForm):
    username = StringField(
      "Username",
      validators=[
        DataRequired(message="Please choose a username."),
        Length(min=3, max=30),
      ]
    )
    
    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Please enter your full name."),
            Length(max=250),
            validate_full_name,
        ]
    )
    
    description = TextAreaField(
        "About",
        validators=[
            Optional(),
            Length(max=1000)
        ]
    )
    
    category = SelectField(
        "Profile Type",
        choices=[
            ("", "Select profile type"),
            ("reader", "Reader"),
            ("writer", "Writer"),
            ("journalist", "Journalist"),
            ("blogger", "Blogger"),
            ("content_creator", "Content Creator"),
            ("analyst", "Analyst"),
            ("other", "Other")
        ],
        validators=[DataRequired(message="Please choose a profile type.")]
    )
    
    location = StringField(
        "Location",
        validators=[
            Optional(),
            Length(max=100),
            Regexp(
                r"^[A-Za-z0-9\s,.'-]*$",
                message="Enter a valid location."
            )
        ]
    )
    
    submit = SubmitField("Save Profile")

class DeletePostForm(FlaskForm):
    submit = SubmitField("Delete")

class SubmitPostForm(FlaskForm):
    submit = SubmitField("Submit")

class AdminTribeForm(FlaskForm):
    tribe_url = StringField(
        "Tribe Conversation URL",
        validators=[
            Optional(),
            URL(message="Please enter a valid Tribe URL."),
            Length(max=500)
        ]
    )

    tribe_title = StringField(
        "Tribe Conversation Title",
        validators=[
            Optional(),
            Length(max=150)
        ]
    )

    tribe_description = TextAreaField(
        "Tribe Conversation Description",
        validators=[
            Optional(),
            Length(max=500)
        ]
    )

    tribe_button_text = StringField(
        "Tribe Button Text",
        validators=[
            Optional(),
            Length(max=100)
        ]
    )

    submit = SubmitField("Save Tribe Conversation")

class RemoveTribeForm(FlaskForm):
    submit = SubmitField("Remove Tribe Conversation")