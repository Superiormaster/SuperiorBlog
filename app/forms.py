from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, BooleanField, FileField, SelectMultipleField, DateTimeField, MultipleFileField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional
from flask_wtf.file import FileAllowed, FileField

class LoginForm(FlaskForm):
    identifier = StringField("Username or Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class PostForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(message="Title is required")])
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

class UserLoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Login")

class PrivacyTermsForm(FlaskForm):
    privacy_policy = TextAreaField(
        "Privacy Policy",
        validators=[DataRequired()]
    )

    terms_conditions = TextAreaField(
        "Terms & Conditions",
        validators=[DataRequired()]
    )

    submit = SubmitField("Save")

class ProfileForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required."),
            Length(min=3, max=80)
        ]
    )

    full_name = StringField(
        "Full Name",
        validators=[
            Optional(),
            Length(max=120)
        ]
    )

    description = TextAreaField(
        "Description",
        validators=[
            Optional(),
            Length(max=1000)
        ]
    )

    category = SelectField(
        "Category",
        choices=[("", " Select category "), ("blogger", "Blogger"), ("writer", "Writer")],
        validators=[
            Optional(),
            Length(max=80)
        ]
    )

    location = StringField(
        "Location",
        validators=[
            Optional(),
            Length(max=50)
        ]
    )

    id_type = SelectField(
        "ID Type",
        choices=[("nin", "NIN"), ("passport", "Passport")],
        validators=[
            Optional(),
            Length(max=50)
        ]
    )
  
    id_number = StringField(
        "Id Number",
        validators=[
            Optional(),
            Length(max=30)
        ]
    )

    phone = StringField(
        "Phone Number",
        validators=[
            Optional(),
            Length(max=30)
        ]
    )

    bank_account = StringField(
        "Bank Account",
        validators=[
            Optional(),
            Length(max=50)
        ]
    )

class DeletePostForm(FlaskForm):
    submit = SubmitField("Delete")

class SubmitPostForm(FlaskForm):
    submit = SubmitField("Submit")
