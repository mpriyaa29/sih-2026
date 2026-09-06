import serial
import time
import face_recognition
import os
from flask import session
import time
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from twilio.rest import Client
from flask import redirect, url_for
from flask import jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

app.secret_key = "lifelink_secret_key"
account_sid = "ACf0b79eea25af113f9545c326d6edec86"
auth_token = "69d0e5cd5d21a1c56b951b1481bb05da"

twilio_number = "+15734554374"

BASE_URL = "https://epidermal-tactics-clarinet.ngrok-free.dev"

# Upload Folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

db_path = os.path.join(
    BASE_DIR,
    'instance',
    'lifelink.db'
)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =========================
# DATABASE MODEL
# =========================

class Citizen(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    fullname = db.Column(db.String(100))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))

    blood_group = db.Column(db.String(10))
    allergies = db.Column(db.String(200))
    diseases = db.Column(db.String(200))

    emergency_contact = db.Column(db.String(20))

    face_image = db.Column(db.String(200))

    fingerprint_id = db.Column(db.Integer)

class MedicalRecord(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    citizen_id = db.Column(
        db.Integer,
        db.ForeignKey('citizen.id')
    )

    allergies = db.Column(db.String(500))

    emergency_contact = db.Column(db.String(20))

    medications = db.Column(db.String(500))

    conditions = db.Column(db.String(500))

    address = db.Column(db.String(500))

    medical_report = db.Column(db.String(200))


class Doctor(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    doctor_id = db.Column(
        db.String(50),
        unique=True
    )

    name = db.Column(
        db.String(100)
    )

    designation = db.Column(
        db.String(100)
    )

    password = db.Column(
        db.String(200)
    )

    blocked_until = db.Column(
        db.String(100)
    )

    deny_count = db.Column(
        db.Integer,
        default=0
    )

class ConsentRequest(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    citizen_id = db.Column(
        db.Integer,
        db.ForeignKey("citizen.id")
    )

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctor.id")
    )

    status = db.Column(
        db.String(20),
        default="Pending"
    )

    request_time = db.Column(
        db.String(100)
    )

class Prescription(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    citizen_id = db.Column(
        db.Integer,
        db.ForeignKey("citizen.id")
    )

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctor.id")
    )

    medicine = db.Column(
        db.String(500)
    )

    dosage = db.Column(
        db.String(200)
    )

    notes = db.Column(
        db.String(500)
    )

    created_at = db.Column(
        db.String(100)
    )

class AuditLog(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    doctor_name = db.Column(
        db.String(100)
    )

    designation = db.Column(
        db.String(100)
    )

    patient_name = db.Column(
        db.String(100)
    )

    access_mode = db.Column(
        db.String(50)
    )

    access_time = db.Column(
        db.String(100)
    )

# =========================
# HOME PAGE
# =========================

@app.route("/")
def home():

    return render_template("index.html")


# =========================
# LOGIN PAGE
# =========================

# =========================
# EMERGENCY LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    # Hard-coded emergency responder credentials
    USERS = {

        "Police Officer": {
            "employee_id": "POL001",
            "password": "Police@123"
        },

        "Ambulance Staff": {
            "employee_id": "AMB001",
            "password": "Ambulance@123"
        },

        "Admin": {
            "employee_id": "ADM001",
            "password": "Admin@123"
        }

    }

    if request.method == "POST":

        role = request.form.get("role")
        employee_id = request.form.get("employee_id")
        password = request.form.get("password")

        # Check whether selected role exists
        if role not in USERS:

            return render_template(
                "login.html",
                error="Please select a valid role."
            )

        user = USERS[role]

        # Verify Employee ID and Password
        if (
            employee_id == user["employee_id"]
            and password == user["password"]
        ):

            # Store login information in session
            session["logged_in"] = True
            session["role"] = role
            session["employee_id"] = employee_id

            return redirect(
                url_for("dashboard")
            )

        # Invalid credentials
        return render_template(
            "login.html",
            error="Invalid Employee ID or Password."
        )

    return render_template("login.html")


# =========================
# REGISTRATION PAGE
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        try:

            fullname = request.form["fullname"]
            age = request.form["age"]
            gender = request.form["gender"]

            blood_group = request.form["blood_group"]
            allergies = request.form["allergies"]
            diseases = request.form["diseases"]

            emergency_contact = request.form["emergency_contact"]

            # =========================
            # FINGERPRINT ID
            # =========================

            fingerprint_id = int(
                request.form["fingerprint_id"]
            )

            # =========================
            # CHECK DUPLICATE ID
            # =========================

            existing_citizen = Citizen.query.filter_by(
                fingerprint_id=fingerprint_id
            ).first()

            if existing_citizen:

                return f"""
                <script>
                    alert("Fingerprint ID {fingerprint_id} is already registered.");
                    window.history.back();
                </script>
                """

            # =========================
            # FACE IMAGE
            # =========================

            file = request.files["face_image"]

            if not file or file.filename == "":
                return "Face image is required."

            filename = secure_filename(
                file.filename
            )

            file.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

            # =========================
            # CREATE CITIZEN
            # =========================

            new_citizen = Citizen(

                fullname=fullname,

                age=age,

                gender=gender,

                blood_group=blood_group,

                allergies=allergies,

                diseases=diseases,

                emergency_contact=emergency_contact,

                face_image=filename,

                fingerprint_id=fingerprint_id
            )

            db.session.add(new_citizen)

            db.session.commit()

            return render_template(
                "success.html"
            )

        except Exception as e:

            db.session.rollback()

            print(
                "Registration Error:",
                e
            )

            return f"Registration failed: {e}"

    return render_template(
        "register.html"
    )

# @app.route("/register", methods=["GET", "POST"])
# def register():

#     if request.method == "POST":

#         fullname = request.form['fullname']
#         age = request.form['age']
#         gender = request.form['gender']

#         blood_group = request.form['blood_group']
#         allergies = request.form['allergies']
#         diseases = request.form['diseases']

#         emergency_contact = request.form['emergency_contact']
#         fingerprint_id = request.form['fingerprint_id']

#         # Upload Face Image
#         file = request.files['face_image']

#         filename = secure_filename(file.filename)

#         file.save(
#             os.path.join(
#                 app.config['UPLOAD_FOLDER'],
#                 filename
#             )
#         )

#         # Save Citizen Data
#         new_citizen = Citizen(

#     fullname=fullname,
#     age=age,
#     gender=gender,

#     blood_group=blood_group,
#     allergies=allergies,
#     diseases=diseases,

#     emergency_contact=emergency_contact,

#     face_image=filename,

#     fingerprint_id=fingerprint_id
# )


#         db.session.add(new_citizen)
#         db.session.commit()

#         return render_template("success.html")

#     return render_template("register.html")


# =========================
# VIEW ALL CITIZENS
# =========================

@app.route("/citizens")
def citizens():

    all_citizens = Citizen.query.all()

    return render_template(
        "citizens.html",
        citizens=all_citizens
    )


# =========================
# EMERGENCY SEARCH
# =========================

@app.route("/emergency", methods=["GET", "POST"])
def emergency():

    citizen = None

    if request.method == "POST":

        search_name = request.form['search']

        citizen = Citizen.query.filter_by(
            fullname=search_name
        ).first()

    return render_template(
        "emergency.html",
        citizen=citizen
    )


# =========================
# FACE SEARCH PAGE
# =========================

@app.route("/face-search")
def face_search():

    return render_template("face_search.html")

# @app.route("/fingerprint-search-manual/<int:fingerprint_id>")
# def fingerprint_search(fingerprint_id):

#     citizen = Citizen.query.filter_by(
#         fingerprint_id=fingerprint_id
#     ).first()

#     if not citizen:

#         return "Citizen not found"

#     return redirect(
#         url_for(
#             "emergency_access",
#             citizen_id=citizen.id
#         )
#     )

@app.route("/fingerprint-search")
def fingerprint_search():

    try:

        arduino = serial.Serial(
            'COM13',
            9600,
            timeout=10
        )

        time.sleep(2)

        while True:

            line = arduino.readline().decode().strip()

            print(line)

            if "Found ID #" in line:

                fingerprint_id = int(
                    line.split("#")[1].split()[0]
                )

                citizen = Citizen.query.filter_by(
                    fingerprint_id=fingerprint_id
                ).first()

                arduino.close()

                if citizen:

                    return render_template(
                        "victim.html",
                        citizen=citizen
                    )

                return "Citizen not found"

    except Exception as e:

        return str(e)

# @app.route("/register-fingerprint")
# def register_fingerprint():

#     try:

#         # Find next available fingerprint ID
#         last_citizen = Citizen.query.order_by(
#             Citizen.fingerprint_id.desc()
#         ).first()

#         if last_citizen and last_citizen.fingerprint_id:
#             fingerprint_id = last_citizen.fingerprint_id + 1
#         else:
#             fingerprint_id = 1

#         arduino = serial.Serial(
#             'COM13',
#             9600,
#             timeout=60
#         )

#         time.sleep(2)

#         # Send ID to Arduino
#         arduino.write(
#             f"{fingerprint_id}\n".encode()
#         )

#         while True:

#             line = arduino.readline().decode().strip()

#             print(line)

#             if "Stored!" in line:

#                 arduino.close()

#                 return jsonify({

#                     "success": True,

#                     "fingerprint_id": fingerprint_id

#                 })

#     except Exception as e:

#         return jsonify({

#             "success": False,

#             "error": str(e)

#         })

# =========================
# DASHBOARD PAGE
# =========================

@app.route("/dashboard")
def dashboard():

    return render_template("dashboard.html")

@app.route("/victim", methods=["GET", "POST"])
def victim():

    citizen = None

    if request.method == "POST":

        uploaded_file = request.files['face_image']

        filename = secure_filename(uploaded_file.filename)

        search_path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            filename
        )

        uploaded_file.save(search_path)

        try:

            # =========================
            # LOAD UPLOADED IMAGE
            # =========================

            unknown_image = face_recognition.load_image_file(
                search_path
            )

            unknown_encodings = face_recognition.face_encodings(
                unknown_image,
                model="small"
            )

            if unknown_encodings:

                print("Uploaded face detected")

                unknown_encoding = unknown_encodings[0]

                citizens = Citizen.query.all()

                for person in citizens:

                    citizen_image_path = os.path.join(
                        app.config['UPLOAD_FOLDER'],
                        person.face_image
                    )

                    # =========================
                    # LOAD REGISTERED IMAGE
                    # =========================

                    known_image = face_recognition.load_image_file(
                        citizen_image_path
                    )

                    known_encodings = face_recognition.face_encodings(
                        known_image,
                        model="small"
                    )

                    if known_encodings:

                        print(
                            "Face encoding success:",
                            person.fullname
                        )

                        known_encoding = known_encodings[0]

                        # =========================
                        # FACE COMPARISON
                        # =========================

                        results = face_recognition.compare_faces(
                            [known_encoding],
                            unknown_encoding,
                            tolerance=0.6
                        )

                        if results[0]:

                            print(
                                "MATCH FOUND:",
                                person.fullname
                            )

                            citizen = person
                            break

                    else:

                        print(
                            "NO FACE FOUND:",
                            person.fullname
                        )

            else:

                print("No face detected in uploaded image")

        except Exception as e:

            print("Face Recognition Error:", e)

    return render_template(
        "victim.html",
        citizen=citizen
    )



@app.route("/gps")
def gps():

    return render_template("gps.html")

@app.route("/send-alert/<int:citizen_id>")
def send_alert(citizen_id):

    citizen = Citizen.query.get(citizen_id)

    if citizen:

        client = Client(account_sid, auth_token)

        latitude = 13.0827
        longitude = 80.2707

        location_link = (
            f"https://maps.google.com/?q={latitude},{longitude}"
        )

        message_body = f"""
ALERT FROM ResQID

Victim Name: {citizen.fullname}

Emergency Detected.

Live GPS Location:
{location_link}
"""
        
        print("Sending SMS to:")
        print("+91" + citizen.emergency_contact)

        message = client.messages.create(

            body=message_body,

            from_=twilio_number,

            to="+91" + citizen.emergency_contact

        )

        print("SMS Sent Successfully!")
        print(message.sid)

    else:

        print("Citizen not found!")

    return redirect(
        url_for(
            'emergency_access',
            citizen_id=citizen.id
        )
    )


@app.route("/emergency-access/<int:citizen_id>")
def emergency_access(citizen_id):

    # Create 2-minute access window
    if "emergency_expiry" not in session:
        session["emergency_expiry"] = time.time() + 120

    # Check expiry
    if time.time() > session["emergency_expiry"]:
        session.pop("emergency_expiry", None)
        return redirect(url_for("dashboard"))

    citizen = Citizen.query.get(citizen_id)

    latest_record = MedicalRecord.query.filter_by(
        citizen_id=citizen_id
    ).order_by(
        MedicalRecord.id.desc()
    ).first()

    remaining = int(
        session["emergency_expiry"] - time.time()
    )

    return render_template(
        "emergency_access.html",
        citizen=citizen,
        record=latest_record,
        remaining=remaining
    )




@app.route("/updatedrecords", methods=["GET", "POST"])
def updatedrecords():

    if request.method == "POST":

        citizen_id = request.form["citizen_id"]

        allergies = request.form["allergies"]

        emergency_contact = request.form["emergency_contact"]

        medications = request.form["medications"]

        conditions = request.form["conditions"]

        address = request.form["address"]

        report_file = request.files["medical_report"]

        report_filename = ""

        if report_file and report_file.filename != "":

            report_filename = secure_filename(
                report_file.filename
            )

            report_file.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    report_filename
                )
            )

        record = MedicalRecord(

            citizen_id=citizen_id,

            allergies=allergies,

            emergency_contact=emergency_contact,

            medications=medications,

            conditions=conditions,

            address=address,

            medical_report=report_filename
        )

        db.session.add(record)

        db.session.commit()

        return render_template(
            "success.html"
        )

    return render_template(
        "updatedrecords.html"
    )

@app.route("/authority")
def authority():

    return render_template("authority.html")

@app.route("/logs")
def logs():

    logs = AuditLog.query.order_by(
        AuditLog.id.desc()
    ).all()

    return render_template(

        "logs.html",

        logs=logs

    )

@app.route("/alerts")
def alerts():

    return render_template("alerts.html")


@app.route(
    "/doctor-login",
    methods=["GET","POST"]
)
def doctor_login():

    if request.method == "POST":

        doctor_id = request.form["doctor_id"]

        password = request.form["password"]

        doctor = Doctor.query.filter_by(
            doctor_id=doctor_id
        ).first()

        if doctor:

            # Check if blocked

            if doctor.blocked_until:

                blocked_time = datetime.fromisoformat(
                    doctor.blocked_until
                )

                if blocked_time > datetime.now():

                    return (
                        "Doctor account blocked "
                        "for 24 hours due to "
                        "multiple denied requests."
                    )

            # Check password

            if doctor.password == password:

                session["doctor_id"] = doctor.id

                return redirect(
                    url_for(
                        "doctor_dashboard"
                    )
                )

        return "Invalid Credentials"

    return render_template(
        "doctor_login.html"
    )

@app.route("/doctor-dashboard")
def doctor_dashboard():

    if "doctor_id" not in session:

        return redirect(
            url_for(
                "doctor_login"
            )
        )

    return render_template(
        "doctor_dashboard.html"
    )

@app.route(
    "/request-access",
    methods=["GET","POST"]
)
def request_access():

    if "doctor_id" not in session:

        return redirect(
            url_for(
                "doctor_login"
            )
        )

    if request.method == "POST":

        citizen_id = request.form["citizen_id"]

        citizen = Citizen.query.get(
            citizen_id
        )

        if not citizen:

            return "Citizen Not Found"

        new_request = ConsentRequest(

            citizen_id=citizen_id,

            doctor_id=session[
                "doctor_id"
            ],

            status="Pending",

            request_time=str(
                datetime.now()
            )
        )

        db.session.add(
            new_request
        )

        db.session.commit()

        approve_link = (
            f"{BASE_URL}/approve-request/{new_request.id}"
        )

        deny_link = (
            f"{BASE_URL}/deny-request/{new_request.id}"
        )

        client = Client(
            account_sid,
            auth_token
        )

        client.messages.create(

            body=f"""
LifeLink Consent Request

Doctor is requesting access
to Citizen ID {citizen_id}

Approve:
{approve_link}

Deny:
{deny_link}
""",

            from_=twilio_number,

            to="+91" + citizen.emergency_contact

        )

        return "SMS sent successfully"

    return render_template(
        "request_access.html"
    )

@app.route(
    "/view-consents"
)
def view_consents():

    requests = ConsentRequest.query.filter_by(
        status="Pending"
    ).all()

    return render_template(
        "consent_notifications.html",
        requests=requests
    )

@app.route("/approve-request/<int:id>")
def approve_request(id):

    request_data = ConsentRequest.query.get(id)

    request_data.status = "Approved"

    doctor = Doctor.query.get(
        request_data.doctor_id
    )

    # Reset deny count after approval
    doctor.deny_count = 0

    db.session.commit()

    return redirect(
        url_for("view_consents")
    )

@app.route(
    "/deny-request/<int:id>"
)
def deny_request(id):

    request_data = ConsentRequest.query.get(id)

    request_data.status = "Denied"

    doctor = Doctor.query.get(
        request_data.doctor_id
    )

    doctor.deny_count += 1

    if doctor.deny_count >= 3:

        doctor.blocked_until = str(
            datetime.now() +
            timedelta(hours=24)
        )

        doctor.deny_count = 0

    db.session.commit()

    return redirect(
        url_for(
            "view_consents"
        )
    )


@app.route("/my-requests")
def my_requests():

    if "doctor_id" not in session:

        return redirect(
            url_for(
                "doctor_login"
            )
        )

    requests = ConsentRequest.query.filter_by(

        doctor_id=session[
            "doctor_id"
        ]

    ).all()

    return render_template(

        "my_requests.html",

        requests=requests

    )

@app.route(
    "/patient-record/<int:citizen_id>"
)
def patient_record(citizen_id):

    if "doctor_id" not in session:

        return redirect(
            url_for(
                "doctor_login"
            )
        )

    citizen = Citizen.query.get(
        citizen_id
    )

    record = MedicalRecord.query.filter_by(
        citizen_id=citizen_id
    ).first()

    doctor = Doctor.query.get(
        session["doctor_id"]
    )

    log = AuditLog(

        doctor_name=doctor.name,

        designation=doctor.designation,

        patient_name=citizen.fullname,

        access_mode="Consent",

        access_time=str(
            datetime.now()
        )
    )

    db.session.add(log)

    db.session.commit()

    return render_template(

        "patient_record.html",

        citizen=citizen,

        record=record

    )

@app.route(
    "/upload-prescription",
    methods=["GET", "POST"]
)
def upload_prescription():

    result = None

    if request.method == "POST":

        citizen_id = request.form["citizen_id"]

        prescription = request.form["prescription"].lower()

        record = MedicalRecord.query.filter_by(
            citizen_id=citizen_id
        ).first()

        if not record:

            result = (
                "Patient Record Not Found",
                []
            )

        else:

            warnings = []

            allergies = (
                record.allergies or ""
            ).lower()

            medications = (
                record.medications or ""
            ).lower()

            conditions = (
                record.conditions or ""
            ).lower()

            # Check allergies

            if "penicillin" in prescription:

                if "allergy" in allergies:

                    warnings.append(
                        "Patient has allergy history."
                    )

            # Check diabetes

            if "diabetes" in conditions:

                if "steroid" in prescription:

                    warnings.append(
                        "Steroids may affect diabetic patient."
                    )

            # Check duplicate medicines

            prescribed_meds = [
                x.strip()
                for x in prescription.split(",")
            ]

            existing_meds = [
                x.strip()
                for x in medications.split(",")
            ]

            for med in prescribed_meds:

                if med.lower() in existing_meds:

                    warnings.append(
                        f"{med} is already being taken."
                    )

            if warnings:

                result = (
                    "Not Suitable",
                    warnings
                )

            else:

                result = (
                    "Suitable",
                    ["No conflicts found."]
                )

    return render_template(
        "upload_prescription.html",
        result=result
    )

# =========================
# CREATE DATABASE
# =========================

with app.app_context():

    db.create_all()

# =========================
# RUN APP
# =========================

with app.app_context():

    doctor = Doctor.query.filter_by(
        doctor_id="DOC001"
    ).first()

    if not doctor:

        new_doctor = Doctor(
            doctor_id="DOC001",
            name="Dr Kumar",
            designation="Emergency Physician",
            password="Doctor@123"
        )

        db.session.add(new_doctor)
        db.session.commit()

        print("Doctor Created")

with app.app_context():

    doctor = Doctor.query.filter_by(
        doctor_id="DOC002"
    ).first()

    if not doctor:

        new_doctor = Doctor(
            doctor_id="DOC002",
            name="Dr Sharma",
            designation="Cardiologist",
            password="Doctor@456"
        )

        db.session.add(new_doctor)
        db.session.commit()

        print("Doctor Created")

if __name__ == "__main__":

    app.run(debug=True)
