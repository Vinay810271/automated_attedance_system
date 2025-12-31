import os
from datetime import datetime, date
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.utils import secure_filename  
import pytz  

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'presence.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "replace_this_with_a_secure_random_key"

db = SQLAlchemy(app)



# Models
class SchoolAuth(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    area = db.Column(db.String(64), nullable=False)
    school_id = db.Column(db.String(64), nullable=False)
    teacher_id = db.Column(db.String(64), nullable=False)
    password = db.Column(db.String(128), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("area", "school_id", name="unique_area_school"),
    )


class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128))
    phone = db.Column(db.String(32))
    department = db.Column(db.String(128))
    password = db.Column(db.String(128))  # plain for demo only — DO NOT in production


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    organization = db.Column(db.String(128))
    password = db.Column(db.String(128))


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128))
    father_name = db.Column(db.String(128))   # NEW
    mobile = db.Column(db.String(32))         # NEW
    photo = db.Column(db.String(256))         # NEW (store file path / URL)
    class_name = db.Column(db.String(64))


# // module for attaindance
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(64), nullable=False)
    class_name = db.Column(db.String(64))
    subject = db.Column(db.String(128))
    day = db.Column(db.String(32))  # user-chosen day value or date label
    status = db.Column(db.String(32))  # Present / Absent / Late
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)  #  of string)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "class_name": self.class_name,
            "subject": self.subject,
            "day": self.day,
            "status": self.status,
            "marked_at": self.marked_at.strftime("%Y-%m-%d %H:%M:%S") if self.marked_at else None
        }



class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.String(32))
    class_name = db.Column(db.String(64))
    subject = db.Column(db.String(128))
    teacher = db.Column(db.String(128))
    room = db.Column(db.String(64))
    date = db.Column(db.Date, default=date.today)

# Uploads folder config
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/idcard")
def idcard_page():
    return render_template("idcard.html")


@app.route("/save_student", methods=["POST"])
def save_student():
    name = request.form.get("name")
    father_name = request.form.get("fatherName")
    mobile = request.form.get("mobile")
    student_id = request.form.get("studentId")
    photo_file = request.files.get("photoUpload")

    if not all([name, student_id]):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    # Save photo
    photo_url = ""
    if photo_file and allowed_file(photo_file.filename):
        filename = secure_filename(student_id + "_" + photo_file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        photo_file.save(filepath)
        photo_url = url_for("static", filename=f"uploads/{filename}")

    # Check if already exists
    existing = Student.query.filter_by(student_id=student_id).first()
    if existing:
        return jsonify({"status": "error", "message": "Student ID already exists"}), 409

    # Save all fields in DB
    student = Student(
        student_id=student_id,
        name=name,
        father_name=father_name,
        mobile=mobile,
        photo=photo_url,
        class_name="N/A"
    )
    db.session.add(student)
    db.session.commit()

    return jsonify({
        "status": "success",
        "data": {
            "name": name,
            "fatherName": father_name,
            "mobile": mobile,
            "studentId": student_id,
            "photo": photo_url or "https://via.placeholder.com/120x140.png?text=Photo"
        }
    })


# Database helpers
def seed_school_auth():
    if SchoolAuth.query.first():
        return

    records = [
        {"area": "CENTRAL", "school_id": "SCH001", "teacher_id": "T001", "password": "123"},
        {"area": "ARA",   "school_id": "SCH002", "teacher_id": "T002", "password": "123"},
        {"area": "SASARAM",   "school_id": "SCH003", "teacher_id": "T003", "password": "123"},
    ]

    for r in records:
        db.session.add(SchoolAuth(**r))

    db.session.commit()

def seed_sample_data():
    # Only seed if DB empty
    if Teacher.query.first():
        return

    t1 = Teacher(teacher_id="T001", name="Niraj Kumar", email="niraj@example.com",
                 phone="9999999999", department="Computer Science", password="123")
    t2 = Teacher(teacher_id="T002", name="Anita Sharma", email="anita@example.com",
                 phone="9888888888", department="Mathematics", password="123")
    db.session.add_all([t1, t2])

    a1 = Admin(admin_id="admin", name="Principal User",
               organization="Presence School", password="123")
    db.session.add(a1)

    s1 = Student(student_id="S001", name="Rohan", class_name="1")
    s2 = Student(student_id="S002", name="Sita", class_name="1")
    s3 = Student(student_id="S003", name="Aman", class_name="2")
    db.session.add_all([s1, s2, s3])

    #  Attendance records (datetime object use kiya)
    att1 = Attendance(
        student_id="S001",
        class_name="1",
        subject="Math",
        day=str(date.today()),   # yeh string reh sakta hai kyunki model string accept karta hai
        status="Present",
        marked_at=datetime.utcnow()   #  datetime object
    )
    att2 = Attendance(
        student_id="S002",
        class_name="1",
        subject="Math",
        day=str(date.today()),
        status="Absent",
        marked_at=datetime.utcnow()
    )
    db.session.add_all([att1, att2])

    # Schedules ke liye date object theek hai
    sched1 = Schedule(time="09:00 - 09:45", class_name="1",
                      subject="Math", teacher="Anita Sharma", room="A1", date=date.today())
    sched2 = Schedule(time="10:00 - 10:45", class_name="2",
                      subject="Science", teacher="Niraj Kumar", room="B1", date=date.today())
    db.session.add_all([sched1, sched2])

    db.session.commit()



def compute_attendance_rate(for_date=None):
    if for_date is None:
        for_date = date.today()
    total = Attendance.query.filter(func.date(Attendance.marked_at) == for_date).count()
    if total == 0:
        return 0
    present = Attendance.query.filter(func.lower(Attendance.status) == "present", func.date(Attendance.marked_at) == for_date).count()
    rate = int((present / total) * 100)
    return rate

# Routes
@app.route("/home")
def home():
    if "school_id" not in session:
        return redirect(url_for("school_page"))
    return render_template("Home.html")


@app.route("/", methods=["GET", "POST"])
def landing():
    return redirect(url_for("school_page"))

@app.route("/school_page", methods=["GET", "POST"])
def school_page():
    if request.method == "GET":
        return render_template("school_login.html")

    data = request.get_json() or {}

    role = data.get("role")

    if role == "teacher":
        teacher_id = data.get("teacher_id")
        area = data.get("area")
        school_id = data.get("school_id")
        password = data.get("password")

        auth = SchoolAuth.query.filter(
            func.upper(SchoolAuth.teacher_id) == teacher_id.upper(),
            func.upper(SchoolAuth.area) == area.upper(),
            func.upper(SchoolAuth.school_id) == school_id.upper(),
            SchoolAuth.password == password
        ).first()

        if not auth:
            return jsonify({"ok": False, "error": "Invalid Area / School / Teacher credentials"}), 401

        t = Teacher.query.filter_by(teacher_id=teacher_id).first()
        if not t:
            return jsonify({"ok": False, "error": "Teacher not found"}), 401

        session.clear()
        session["role"] = "teacher"
        session["user_id"] = t.teacher_id
        session["area"] = area
        session["school_id"] = school_id
        session["name"] = t.name

        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Invalid role"}), 400


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        return render_template("Login.html")
    # POST JSON login call from front-end
    data = request.get_json() or {}
    role = data.get("role")
    user_id = data.get("user_id")
    password = data.get("password")
    security_key = data.get("security_key")  # used for admin in some front-end code

    if role == "teacher":
        t = Teacher.query.filter_by(teacher_id=user_id, password=password).first()
        if t:
            session.clear()
            session["role"] = "teacher"
            session["user_id"] = t.teacher_id
            session["name"] = t.name
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Invalid teacher credentials"}), 401

    if role == "admin":
        a = Admin.query.filter_by(admin_id=user_id, password=password).first()
        if a:
            # security_key is optional depending on front-end; here we accept if exists
            session.clear()
            session["role"] = "admin"
            session["user_id"] = a.admin_id
            session["name"] = a.name
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Invalid admin credentials"}), 401

    return jsonify({"ok": False, "error": "Invalid role"}), 400


@app.route("/register_teacher", methods=["POST"])
def register_teacher():
    data = request.get_json() or {}
    name = data.get("name")
    teacher_id = data.get("teacher_id")
    password = data.get("password")
    subject = data.get("subject")

    if not (name and teacher_id and password):
        return jsonify({"ok": False, "error": "Missing fields"}), 400

    if Teacher.query.filter_by(teacher_id=teacher_id).first():
        return jsonify({"ok": False, "error": "Teacher ID already exists"}), 409

    t = Teacher(teacher_id=teacher_id, name=name, department=subject, password=password)
    db.session.add(t)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/register_admin", methods=["POST"])
def register_admin():
    data = request.get_json() or {}
    name = data.get("name")
    admin_id = data.get("admin_id")
    password = data.get("password")
    organization = data.get("organization")

    if not (name and admin_id and password):
        return jsonify({"ok": False, "error": "Missing fields"}), 400

    if Admin.query.filter_by(admin_id=admin_id).first():
        return jsonify({"ok": False, "error": "Admin ID exists"}), 409

    a = Admin(admin_id=admin_id, name=name, organization=organization, password=password)
    db.session.add(a)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))



# Teacher dashboard
@app.route("/idcard")
def idcard():
    return render_template("idcard.html")

@app.route("/dashboard")
def dashboard():
    
    if session.get("role") != "teacher":
        return redirect(url_for("login_page"))

    # sample teacher details - match Dashboard.html Jinja keys
    teacher = Teacher.query.filter_by(teacher_id=session.get("user_id")).first()
    if not teacher:
        # fallback to first teacher
        teacher = Teacher.query.first()

    # summary keys expected by Dashboard.html
    summary = {
        "classes": 5,
        "students": Student.query.count(),
        "attendance": compute_attendance_rate(),
        "subjects": 6,
        "tasks": 2
    }

    # notifications and activities (demo)
    notifications = [
        {"msg": "Monthly staff meeting at 3pm", "time": "2h"},
        {"msg": "Update class register", "time": "1d"},
    ]
    activities = [
        {"msg": "Marked attendance for Class 1", "time": "3h"},
        {"msg": "Approved leave for Sita", "time": "1d"},
    ]

    # records used in Subjects & Students table
    records = [
        {"subject": "Math", "class": "1", "students": 30, "attendance": "90%"},
        {"subject": "Science", "class": "2", "students": 28, "attendance": "88%"},
    ]

    return render_template("Dashboard.html",
                           teacher=teacher,
                           summary=summary,
                           notifications=notifications,
                           activities=activities,
                           records=records)


# Admin dashboard and admin pages

@app.route("/admin")
def admin_panel():
    if session.get("role") != "admin":
        return redirect(url_for("login_page"))

    # Get the admin user from database
    admin = Admin.query.filter_by(admin_id=session.get("user_id")).first()
    if not admin:
        return redirect(url_for("login_page"))

    teachers = Teacher.query.all()
    students = Student.query.all()
    attendance_today = Attendance.query.filter(func.date(Attendance.marked_at) == date.today()).all()
    schedules_today = Schedule.query.filter(Schedule.date == date.today()).all()
    attendance_rate = compute_attendance_rate()

    # Create summary data for admin dashboard - matching what Admin.html expects
    summary = {
        "classes": db.session.query(Student.class_name).distinct().count(),  # Count distinct classes
        "students": Student.query.count(),  # Total students
        "attendance": attendance_rate,  # Attendance rate for today
        "subjects": Schedule.query.with_entities(Schedule.subject).distinct().count(),  # Distinct subjects
        "tasks": 2  # Placeholder value for tasks
    }

    return render_template("Admin.html",
                           teacher=admin,  # Pass admin as teacher for template compatibility
                           summary=summary,  # Add the missing summary variable
                           teachers=teachers,
                           students=students,
                           attendance_today=attendance_today,
                           schedules_today=schedules_today,
                           attendance_rate=attendance_rate)
    
# Attendance pages + APIs
@app.route("/attendance_history")
def attendance_history():
    return render_template("attendance_history.html")

@app.route("/attendance")
def attendance_page():
    return render_template("attendance.html")  



@app.route("/attendance_view")
def attendance_view_page():
    return render_template("attendance_view.html")




@app.route("/save_attendance", methods=["POST"])
def save_attendance():
    data = request.get_json()
    if not data:
        return jsonify({"error": "no data received"}), 400

    entries = data if isinstance(data, list) else [data]
    saved_count = 0
    ist = pytz.timezone("Asia/Kolkata")

    for e in entries:
        sid = e.get("student_id") or e.get("id") or e.get("student") or ""
        if not sid:
            continue

        #  Date handling with IST
        date_str = e.get("date")
        if date_str:
            try:
                marked_date = datetime.strptime(date_str, "%Y-%m-%d")
                marked_date = ist.localize(marked_date).astimezone(pytz.utc)
            except Exception:
                marked_date = datetime.now(ist).astimezone(pytz.utc)
        else:
            marked_date = datetime.now(ist).astimezone(pytz.utc)

        a = Attendance(
            student_id=str(sid),
            class_name=e.get("class_name") or e.get("class") or "",
            subject=e.get("subject") or "",
            day=e.get("day") or "",
            status=e.get("status") or "Present",
            marked_at=marked_date
        )
        db.session.add(a)
        saved_count += 1        

    db.session.commit()
    return jsonify({"saved": saved_count}), 201



@app.route("/get_attendance", methods=["GET"])
def get_attendance():
    date_str = request.args.get("date", None)
    class_name = request.args.get("class")
    subject = request.args.get("subject")
    day = request.args.get("day")

    q = Attendance.query
    if date_str:
        try:
            q = q.filter(func.date(Attendance.marked_at) == date_str)
        except Exception:
            pass

    if class_name:
        q = q.filter(Attendance.class_name == class_name)
    if subject:
        q = q.filter(Attendance.subject == subject)
    if day:
        q = q.filter(Attendance.day == day)

    q = q.order_by(Attendance.marked_at.desc())
    results = [r.to_dict() for r in q.all()]   #  now works because to_dict() added
    return jsonify(results), 200



@app.route("/reset_attendance", methods=["POST"])
def reset_attendance():
    try:
        num_deleted = db.session.query(Attendance).delete()
        db.session.commit()
        return jsonify({"message": f"Deleted {num_deleted} records"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500



# Management placeholder endpoints

@app.route("/teachers")
def teachers_page():
    teachers = Teacher.query.all()
    return jsonify([{"teacher_id": t.teacher_id, "name": t.name, "department": t.department} for t in teachers])


@app.route("/students")
def students_page():
    students = Student.query.all()
    return jsonify([{"student_id": s.student_id, "name": s.name, "class": s.class_name} for s in students])


@app.route("/reports")
def reports_page():
    # simple placeholder returning aggregated counts
    total_teachers = Teacher.query.count()
    total_students = Student.query.count()
    attendance_today = Attendance.query.filter(func.date(Attendance.marked_at) == date.today()).count()
    return jsonify({"total_teachers": total_teachers, "total_students": total_students, "attendance_today": attendance_today})


@app.route("/settings")
def settings_page():
    return jsonify({"ok": True, "msg": "Settings placeholder"})



# Run

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_sample_data()
        seed_school_auth()

    app.run(debug=True, host="127.0.0.1", port=5000)

