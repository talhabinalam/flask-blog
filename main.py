from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_mail import Mail
import json
import math
import os
from datetime import datetime

with open("config.json", "r") as c:
    parameters = json.load(c)["parameters"]

local_server = True
app = Flask(__name__)
app.secret_key = "super-secret-key"
app.config["UPLOAD_FOLDER"] = parameters["upload_location"]
app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT="465",
    MAIL_USE_SSL=True,
    MAIL_USERNAME=parameters["gmail-user"],
    MAIL_PASSWORD=parameters["gmail-password"],
)
mail = Mail(app)
if local_server:
    app.config["SQLALCHEMY_DATABASE_URI"] = parameters["local_uri"]
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = parameters["production_uri"]
db = SQLAlchemy(app)


class Contacts(db.Model):
    s_no = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(11), nullable=False)
    message = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)


class Posts(db.Model):
    s_no = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    tag_line = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(30), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(12), nullable=True)


@app.route("/")
def home():
    posts = Posts.query.filter_by().all()  # [0 : parameters["no_of_posts"]]
    last = math.ceil(len(posts) / int(parameters["no_of_posts"]))
    page = request.args.get("page")
    if not str(page).isnumeric():
        page = 1
    page = int(page)
    posts = posts[
        (page - 1)
        * int(parameters["no_of_posts"]) : (page - 1)
        * int(parameters["no_of_posts"])
        + int(parameters["no_of_posts"])
    ]
    if page == 1:
        prev = "#"
        next = "/?page=" + str(page + 1)
    elif page == last:
        prev = "/?page=" + str(page - 1)
        next = "#"
    else:
        prev = "/?page=" + str(page - 1)
        next = "/?page=" + str(page + 1)

    return render_template(
        "index.html", parameters=parameters, posts=posts, prev=prev, next=next
    )


@app.route("/about")
def about():
    return render_template("about.html", parameters=parameters)


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" in session and session["user"] == parameters["admin_user"]:
        posts = Posts.query.all()
        return render_template("dashboard.html", parameters=parameters, posts=posts)
    if request.method == "POST":
        username = request.form.get("email")
        userpaass = request.form.get("pass")
        if (
            username == parameters["admin_user"]
            and userpaass == parameters["admin_pass"]
        ):
            session["user"] = username
            posts = Posts.query.all()
            return render_template("dashboard.html", parameters=parameters, posts=posts)
    return render_template("login.html", parameters=parameters)


@app.route("/post/<string:post_slug>", methods=["GET"])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template("post.html", parameters=parameters, post=post)


@app.route("/edit/<string:s_no>", methods=["GET", "POST"])
def edit(s_no):
    if "user" in session and session["user"] == parameters["admin_user"]:
        if request.method == "POST":
            title = request.form.get("title")
            tag_line = request.form.get("tag_line")
            slug = request.form.get("slug")
            content = request.form.get("content")
            img_file = request.form.get("img_file")
            date = datetime.now()

            if s_no == "0":
                post = Posts(
                    title=title,
                    tag_line=tag_line,
                    slug=slug,
                    content=content,
                    img_file=img_file,
                    date=date,
                )
                db.session.add(post)
                db.session.commit()
            else:
                post = Posts.query.filter_by(s_no=s_no).first()
                post.title = title
                post.tag_line = tag_line
                post.slug = slug
                post.content = content
                post.img_file = img_file
                post.date = date
                db.session.commit()
                return redirect("/edit/" + s_no)
        post = Posts.query.filter_by(s_no=s_no).first()
        return render_template("edit.html", parameters=parameters, post=post, s_no=s_no)


@app.route("/uploader", methods=["GET", "POST"])
def uploader():
    if "user" in session and session["user"] == parameters["admin_user"]:
        if request.method == "POST":
            try:
                f = request.files["file"]
                filename = secure_filename(f.filename)
                f.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                return "Uploaded Successfully"
            except Exception as e:
                return "Error: " + str(e)
        else:
            return "Invalid Request"
    else:
        return "You are not authorized to access this page"


@app.route("/logout")
def logout():
    session.pop("user")
    return redirect("/dashboard")


@app.route("/delete/<string:s_no>", methods=["GET", "POST"])
def delete(s_no):
    if "user" in session and session["user"] == parameters["admin_user"]:
        post = Posts.query.filter_by(s_no=s_no).first()
        db.session.delete(post)
        db.session.commit()
    return redirect("/dashboard")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        """Add entry to the database"""
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        message = request.form.get("message")
        entry = Contacts(
            name=name,
            email=email,
            phone=phone,
            message=message,
            date=datetime.now(),
        )
        db.session.add(entry)
        db.session.commit()
        mail.send_message(
            "New message from " + name,
            sender=email,
            recipients=[parameters["gmail-user"]],
            body=message + "\n" + phone,
        )
    return render_template("contact.html", parameters=parameters)


app.run(debug=True)  # Activate auto debugging
