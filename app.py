import os
import re
from flask import Flask, render_template, request, redirect, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import PyPDF2

app = Flask(__name__)
app.secret_key = "secret123"

# ================= DATABASE CONFIG =================

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///resume.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "resumes"

db = SQLAlchemy(app)

# ================= DATABASE MODELS =================

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))   # removed unique=True
    password = db.Column(db.String(100))
    role = db.Column(db.String(20))
    company = db.Column(db.String(100))


class Candidate(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    company = db.Column(db.String(100))
    resume_filename = db.Column(db.String(200))
    score = db.Column(db.Integer)
    status = db.Column(db.String(50), default="Pending")
    offer_letter = db.Column(db.Text)
    joining_letter = db.Column(db.Text)


# ================= RESUME TEXT EXTRACTION =================

def extract_text(file_path):

    text = ""

    with open(file_path, "rb") as file:

        reader = PyPDF2.PdfReader(file)

        for page in reader.pages:
            text += page.extract_text() or ""

    return text.lower()


# ================= RESUME SCORING =================

def calculate_score(resume_text):

    resume_text = resume_text.lower()

    words = resume_text.split()
    total_words = len(words)

    length_score = min(total_words / 500, 1)

    skill_keywords = [
        "skills","technical skills","programming",
        "c","c++","python","java","sql",
        "matlab","iot","embedded","cadence",
        "html","css","javascript"
    ]

    skill_hits = sum(keyword in resume_text for keyword in skill_keywords)
    skill_score = min(skill_hits / 8, 1)

    internship_score = 1 if "intern" in resume_text else 0
    project_score = 1 if "project" in resume_text else 0

    education_score = 0
    if "engineering" in resume_text:
        education_score += 0.5
    if "cgpa" in resume_text or "%" in resume_text:
        education_score += 0.5

    education_score = min(education_score,1)

    experience_score = 0
    match = re.search(r"(\d+)\+?\s+years", resume_text)

    if match:
        years = int(match.group(1))
        experience_score = min(years / 5, 1)

    final_score = (
        0.25 * length_score +
        0.25 * skill_score +
        0.15 * internship_score +
        0.15 * project_score +
        0.10 * education_score +
        0.10 * experience_score
    )

    score = int(final_score * 10)

    if score < 3:
        score = 3

    if score > 10:
        score = 10

    return score


# ================= HOME =================

@app.route("/")
def home():
    return render_template("login.html")


# ================= REGISTER =================

@app.route("/register", methods=["POST"])
def register():

    username = request.form["username"]
    password = request.form["password"]
    role = request.form["role"]
    company = request.form.get("company")

    # check duplicate username + role
    existing_user = User.query.filter_by(username=username, role=role).first()

    if existing_user:
        return "User already exists with this role. Please use another username."

    new_user = User(
        username=username,
        password=password,
        role=role,
        company=company
    )

    db.session.add(new_user)
    db.session.commit()

    return redirect("/")


# ================= LOGIN =================

@app.route("/login", methods=["POST"])
def login():

    username = request.form["username"]
    password = request.form["password"]
    role = request.form["role"]

    user = User.query.filter_by(
        username=username,
        password=password,
        role=role
    ).first()

    if user:

        session["user"] = username
        session["role"] = role

        if role == "HR":
            return redirect("/hr_dashboard")
        else:
            return redirect("/candidate_dashboard")

    return "Invalid Credentials"


# ================= CANDIDATE DASHBOARD =================

@app.route("/candidate_dashboard")
def candidate_dashboard():

    username = session.get("user")

    companies = User.query.filter_by(role="HR").all()

    applications = Candidate.query.filter_by(username=username).all()

    return render_template(
        "candidate_dashboard.html",
        companies=companies,
        applications=applications
    )


# ================= UPLOAD RESUME =================

@app.route("/upload_resume", methods=["POST"])
def upload_resume():

    file = request.files["resume"]
    company = request.form["company"]
    username = session.get("user")

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)

    file.save(filepath)

    text = extract_text(filepath)

    score = calculate_score(text)

    candidate = Candidate(
        username=username,
        company=company,
        resume_filename=file.filename,
        score=score
    )

    db.session.add(candidate)
    db.session.commit()

    return redirect("/candidate_dashboard")


# ================= HR DASHBOARD =================

@app.route("/hr_dashboard")
def hr_dashboard():

    hr_username = session.get("user")

    hr = User.query.filter_by(username=hr_username).first()

    candidates = Candidate.query.filter_by(company=hr.company).all()

    return render_template(
        "hr_dashboard.html",
        candidates=candidates
    )


# ================= VIEW RESUME =================

@app.route("/view_resume/<filename>")
def view_resume(filename):

    return send_from_directory("resumes", filename)


# ================= APPROVE =================

@app.route("/approve/<int:id>")
def approve(id):

    candidate = Candidate.query.get(id)

    candidate.status = "Approved"

    candidate.offer_letter = f"Dear {candidate.username}, you are selected."

    candidate.joining_letter = "Joining Date : 1st June"

    db.session.commit()

    return redirect("/hr_dashboard")


# ================= REJECT =================

@app.route("/reject/<int:id>")
def reject(id):

    candidate = Candidate.query.get(id)

    candidate.status = "Rejected"

    db.session.commit()

    return redirect("/hr_dashboard")


# ================= RUN APP =================

if __name__ == "__main__":

    os.makedirs("resumes", exist_ok=True)

    with app.app_context():
        db.create_all()

    app.run(debug=True)