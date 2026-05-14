from flask import Flask, request, jsonify, session, render_template, send_from_directory, Response
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from models import db, User, Doctor, Appointment, AppointmentChangeHistory, MedicalRecord, Prescription, Notification
import os
import threading
from datetime import datetime, timedelta
from sqlalchemy import func
import csv
import io
import re

app = Flask(__name__, 
            template_folder='../frontend/templates',
            static_folder='../frontend/static')
app.config['SECRET_KEY'] = 'hospital_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
TIME_SLOTS = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "14:00", "14:30", "15:00", "15:30", "16:00"]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('../frontend/static', path)

CORS(app, supports_credentials=True)
bcrypt = Bcrypt(app)
db.init_app(app)
mail = Mail(app)

login_manager = LoginManager(app)

def send_async_email(subject, recipient, body):
    def send_mail_task(app, msg):
        with app.app_context():
            try:
                mail.send(msg)
            except Exception as e:
                print(f"CRITICAL: Failed to send email to {recipient}. Error: {str(e)}")
                print(f"Check your MAIL_USERNAME and MAIL_PASSWORD environment variables.")

    if not recipient:
        return
    
    # Verify if email is configured
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        print(f"WARNING: Email not sent to {recipient} because MAIL_USERNAME/MAIL_PASSWORD are not set.")
        print(f"Notification Content: {body}")
        return

    msg = Message(subject, recipients=[recipient])
    msg.body = body
    
    # Start a background thread to send the email
    thread = threading.Thread(target=send_mail_task, args=(app, msg))
    thread.start()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    conn = db.engine.raw_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("CREATE TABLE IF NOT EXISTS doctor (id INTEGER PRIMARY KEY, name VARCHAR(100) NOT NULL, specialization VARCHAR(100) NOT NULL, availability VARCHAR(200) NOT NULL)")
    cur.execute("PRAGMA table_info(doctor)")
    cols = [r[1] for r in cur.fetchall()]
    if 'user_id' not in cols:
        try:
            cur.execute("ALTER TABLE doctor ADD COLUMN user_id INTEGER")
        except Exception:
            pass
    cur.execute("CREATE TABLE IF NOT EXISTS user (id INTEGER PRIMARY KEY, username VARCHAR(80) NOT NULL UNIQUE, password VARCHAR(120) NOT NULL, role VARCHAR(20) NOT NULL, full_name VARCHAR(100) NOT NULL)")
    cur.execute("PRAGMA table_info(user)")
    ucols = [r[1] for r in cur.fetchall()]
    if 'email' not in ucols:
        try:
            cur.execute("ALTER TABLE user ADD COLUMN email VARCHAR(120)")
        except Exception:
            pass
    cur.execute("CREATE TABLE IF NOT EXISTS appointment (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, doctor_id INTEGER, appointment_date VARCHAR(20) NOT NULL, appointment_time VARCHAR(10) NOT NULL, status VARCHAR(20), reason TEXT, created_at DATETIME)")
    cur.execute("PRAGMA table_info(appointment)")
    acols = [r[1] for r in cur.fetchall()]
    if 'specialization' not in acols:
        try:
            cur.execute("ALTER TABLE appointment ADD COLUMN specialization VARCHAR(100) DEFAULT 'General Physician'")
        except Exception:
            pass
    if 'urgent' not in acols:
        try:
            cur.execute("ALTER TABLE appointment ADD COLUMN urgent BOOLEAN DEFAULT 0")
        except Exception:
            pass
    conn.commit()
    cur.close()
    conn.close()
    db.create_all()
    # Ensure default admin exists
    admin_user = User.query.filter_by(username='admin').first()
    if admin_user is None:
        hashed_pw = bcrypt.generate_password_hash('staff123').decode('utf-8')
        admin_user = User(username='admin', password=hashed_pw, role='admin', full_name='Hospital Administrator')
        db.session.add(admin_user)
    else:
        admin_user.role = 'admin'
    db.session.commit()

def parse_date(d):
    return datetime.strptime(d, "%Y-%m-%d").date()

def parse_time(t):
    return datetime.strptime(t, "%H:%M").time()

def is_past(date_str, time_str):
    dt = datetime.combine(parse_date(date_str), parse_time(time_str))
    return dt < datetime.now()

def get_available_doctor(specialization, date_str, time_str):
    doctors = Doctor.query.filter_by(specialization=specialization).all()
    for d in doctors:
        exists = Appointment.query.filter(
            Appointment.doctor_id == d.id,
            Appointment.appointment_date == date_str,
            Appointment.appointment_time == time_str,
            Appointment.status.in_(['Pending', 'Confirmed'])
        ).first()
        if not exists:
            return d
    return None

def create_notification(user_id, content, type_):
    n = Notification(user_id=user_id, content=content, type=type_)
    db.session.add(n)
    db.session.commit()
    
    # Send email notification
    user = User.query.get(user_id)
    if user and user.email:
        # Create a more descriptive subject
        subjects = {
            'appointment_booked': 'Appointment Confirmation - UniHealth',
            'new_assignment': 'New Patient Assignment - UniHealth',
            'status_update': 'Appointment Status Update - UniHealth',
            'appointment_cancelled': 'Appointment Cancellation Alert - UniHealth',
            'reschedule': 'Appointment Reschedule Notification - UniHealth',
            'transfer': 'Patient Transfer Notification - UniHealth',
            'medical_record': 'New Medical Record Added - UniHealth',
            'prescription': 'New Digital Prescription Issued - UniHealth'
        }
        subject = subjects.get(type_, f"UniHealth Notification: {type_.replace('_', ' ').title()}")
        send_async_email(subject, user.email, content)
    return n

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    full_name = data.get('full_name')
    email = data.get('email')

    if not all([username, password, full_name, email]):
        return jsonify({'message': 'All fields are required'}), 400
    
    if len(password) < 6:
        return jsonify({'message': 'Password must be at least 6 characters long'}), 400

    # Email validation: allow any valid email address
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({'message': 'Please provide a valid email address'}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({'message': 'Username or email already exists'}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, password=hashed_pw, full_name=full_name, email=email, role='student')
    db.session.add(new_user)
    db.session.commit()
    
    # Send signup confirmation email
    try:
        send_async_email(
            "Welcome to UniHealth JKUAT",
            email,
            f"Hello {full_name},\n\nThank you for registering with UniHealth JKUAT Hospital Management System. Your account has been successfully created.\n\nYou can now log in to book appointments and manage your health records.\n\nBest regards,\nUniHealth Team"
        )
    except Exception as e:
        print(f"Signup email failed to queue: {str(e)}")
    
    return jsonify({'message': 'Registered successfully. A confirmation email has been sent to your school email.'}), 201

@app.route('/appointments/<int:id>/transfer', methods=['POST'])
@login_required
def transfer_appointment(id):
    if current_user.role != 'doctor':
        return jsonify({'message': 'Only doctors can transfer patients'}), 403
    
    appointment = Appointment.query.get_or_404(id)
    current_doc = Doctor.query.filter_by(user_id=current_user.id).first()
    
    if not current_doc or appointment.doctor_id != current_doc.id:
        return jsonify({'message': 'This appointment is not assigned to you'}), 403
        
    data = request.json
    new_doctor_id = data.get('doctor_id')
    transfer_reason = data.get('reason', 'No reason provided')
    new_doc = Doctor.query.get_or_404(new_doctor_id)
    
    # Check if the new doctor is available at the original slot
    exists = Appointment.query.filter(
        Appointment.doctor_id == new_doc.id,
        Appointment.appointment_date == appointment.appointment_date,
        Appointment.appointment_time == appointment.appointment_time,
        Appointment.status.in_(['Pending', 'Confirmed'])
    ).first()
    
    if exists:
        return jsonify({'message': f'Dr. {new_doc.name} is already booked for this slot'}), 400
        
    old_doc_name = current_doc.name
    appointment.doctor_id = new_doc.id
    db.session.commit()
    
    # Notify student
    create_notification(appointment.student_id, f"Your appointment on {appointment.appointment_date} at {appointment.appointment_time} has been transferred from Dr. {old_doc_name} to Dr. {new_doc.name}. Note: {transfer_reason}", 'transfer')
    # Notify new doctor
    if new_doc.user_id:
        create_notification(new_doc.user_id, f"New patient transfer: {appointment.student.full_name} for {appointment.appointment_date} at {appointment.appointment_time}. Briefing: {transfer_reason}", 'transfer')
        
    return jsonify({'message': 'Patient transferred successfully'})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if user and bcrypt.check_password_hash(user.password, password):
        login_user(user)
        return jsonify({
            'message': 'Logged in successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'full_name': user.full_name
            }
        })
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'})

@app.route('/me', methods=['GET'])
@login_required
def get_me():
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'role': current_user.role,
        'full_name': current_user.full_name
    })

@app.route('/doctors', methods=['GET'])
def get_doctors():
    doctors = Doctor.query.all()
    return jsonify([{
        'id': d.id,
        'name': d.name,
        'specialization': d.specialization,
        'availability': d.availability
    } for d in doctors])

@app.route('/admin/doctors', methods=['POST'])
@login_required
def create_doctor():
    if current_user.role != 'admin':
        return jsonify({'message': 'Forbidden'}), 403
    data = request.json
    name = data.get('name')
    specialization = data.get('specialization')
    availability = data.get('availability', '')
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    if username and User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400
    if email and User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 400
    user = None
    if username and password:
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password=hashed_password, role='doctor', full_name=name, email=email)
        db.session.add(user)
        db.session.flush()
    doctor = Doctor(name=name, specialization=specialization, availability=availability, user_id=user.id if user else None)
    db.session.add(doctor)
    db.session.commit()
    
    # Notify doctor of account creation
    if email and username and password:
        send_async_email(
            "Welcome to UniHealth JKUAT - Doctor Account Created",
            email,
            f"Hello Dr. {name},\n\nYour professional account at UniHealth JKUAT has been created by the administrator.\n\nLogin Credentials:\nUsername: {username}\nPassword: {password}\n\nPlease log in to manage your appointments and patient records.\n\nBest regards,\nUniHealth Admin"
        )
        
    return jsonify({'message': 'Doctor created', 'id': doctor.id}), 201

@app.route('/admin/doctors', methods=['GET'])
@login_required
def list_doctors_admin():
    if current_user.role not in ['admin', 'doctor']:
        return jsonify({'message': 'Forbidden'}), 403
    doctors = Doctor.query.all()
    res = []
    for d in doctors:
        username = None
        if d.user_id:
            u = User.query.get(d.user_id)
            if u:
                username = u.username
        res.append({'id': d.id, 'name': d.name, 'specialization': d.specialization, 'availability': d.availability, 'user_id': d.user_id, 'username': username})
    return jsonify(res)

@app.route('/admin/doctors/<int:id>', methods=['PATCH', 'DELETE'])
@login_required
def modify_doctor(id):
    if current_user.role != 'admin':
        return jsonify({'message': 'Forbidden'}), 403
    doctor = Doctor.query.get_or_404(id)
    if request.method == 'DELETE':
        # If doctor has a linked user account, delete it too
        if doctor.user_id:
            user = User.query.get(doctor.user_id)
            if user:
                db.session.delete(user)
        db.session.delete(doctor)
        db.session.commit()
        return jsonify({'message': 'Doctor and associated account deleted'})
    
    data = request.json
    doctor.name = data.get('name', doctor.name)
    doctor.specialization = data.get('specialization', doctor.specialization)
    doctor.availability = data.get('availability', doctor.availability)
    
    # Optional: Update user account details if provided
    if doctor.user_id:
        user = User.query.get(doctor.user_id)
        if user:
            user.full_name = doctor.name
            if 'username' in data:
                user.username = data['username']
            if 'password' in data and data['password']:
                user.password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
                
    db.session.commit()
    return jsonify({'message': 'Doctor updated'})

@app.route('/timeslots', methods=['GET'])
def get_timeslots():
    date_str = request.args.get('date')
    specialization = request.args.get('specialization')
    if not date_str or not specialization:
        return jsonify({'message': 'Missing parameters'}), 400
    
    # Get all doctors for this specialization
    doctors = Doctor.query.filter_by(specialization=specialization).all()
    if not doctors:
        return jsonify({'date': date_str, 'specialization': specialization, 'available': []})
    
    doctor_ids = [d.id for d in doctors]
    available_slots = []
    
    for slot in TIME_SLOTS:
        # Prevent booking past times for today
        if is_past(date_str, slot):
            continue
            
        # Check how many doctors are busy at this slot
        busy_count = Appointment.query.filter(
            Appointment.appointment_date == date_str,
            Appointment.appointment_time == slot,
            Appointment.doctor_id.in_(doctor_ids),
            Appointment.status.in_(['Pending', 'Confirmed'])
        ).count()
        
        # If at least one doctor is free, the slot is available
        if busy_count < len(doctors):
            available_slots.append(slot)
            
    return jsonify({'date': date_str, 'specialization': specialization, 'available': available_slots})

@app.route('/appointments', methods=['POST'])
@login_required
def book_appointment():
    data = request.json
    specialization = data.get('specialization')
    date = data.get('date')
    time = data.get('time')
    reason = data.get('reason')
    urgent = bool(data.get('urgent', False))
    if is_past(date, time):
        return jsonify({'message': 'Cannot book in the past'}), 400
    doctor = get_available_doctor(specialization, date, time)
    if doctor is None:
        return jsonify({'message': 'No available doctor for the selected slot'}), 400

    new_appointment = Appointment(
        student_id=current_user.id,
        doctor_id=doctor.id,
        specialization=specialization,
        appointment_date=date,
        appointment_time=time,
        reason=reason,
        status='Pending',
        urgent=urgent
    )
    db.session.add(new_appointment)
    db.session.commit()
    
    # Notify student
    create_notification(current_user.id, f"Your appointment for {specialization} on {date} at {time} has been booked successfully with Dr. {doctor.name}.", 'appointment_booked')
    
    # Notify doctor
    if doctor.user_id:
        create_notification(doctor.user_id, f"New appointment assigned: {current_user.full_name} has booked a {specialization} slot on {date} at {time}.", 'new_assignment')
    
    return jsonify({'message': 'Appointment booked successfully', 'id': new_appointment.id}), 201

@app.route('/appointments', methods=['GET'])
@login_required
def get_appointments():
    if current_user.role == 'student':
        appointments = Appointment.query.filter_by(student_id=current_user.id).all()
    elif current_user.role == 'doctor':
        doctor = Doctor.query.filter_by(user_id=current_user.id).first()
        if doctor is None:
            appointments = []
        else:
            appointments = Appointment.query.filter_by(doctor_id=doctor.id).all()
    else:
        appointments = Appointment.query.all()

    return jsonify([{
        'id': a.id,
        'doctor_name': a.doctor.name if a.doctor else None,
        'student_name': a.student.full_name,
        'specialization': a.specialization,
        'date': a.appointment_date,
        'time': a.appointment_time,
        'status': a.status,
        'reason': a.reason,
        'urgent': a.urgent
    } for a in appointments])

@app.route('/appointments/<int:id>/status', methods=['PATCH'])
@login_required
def update_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    data = request.json
    status = data.get('status')
    if current_user.role == 'student' and status != 'Cancelled':
        return jsonify({'message': 'Students can only cancel appointments'}), 403
    if status:
        appointment.status = status
    db.session.commit()
    
    status_msg = f"Your appointment on {appointment.appointment_date} at {appointment.appointment_time} has been {appointment.status}."
    if appointment.status == 'Cancelled':
        status_msg = f"Your appointment on {appointment.appointment_date} at {appointment.appointment_time} has been CANCELLED."
        # If student cancelled, notify doctor
        if current_user.role == 'student' and appointment.doctor and appointment.doctor.user_id:
            create_notification(appointment.doctor.user_id, f"Appointment Cancelled: Student {current_user.full_name} has cancelled their appointment for {appointment.appointment_date} at {appointment.appointment_time}.", 'appointment_cancelled')
    elif appointment.status == 'Confirmed':
        status_msg = f"Your appointment on {appointment.appointment_date} at {appointment.appointment_time} is now CONFIRMED. Please be on time."
    elif appointment.status == 'Completed':
        status_msg = f"Your appointment on {appointment.appointment_date} at {appointment.appointment_time} has been marked as COMPLETED. You can now view your medical records and prescriptions."
        
    create_notification(appointment.student_id, status_msg, 'status_update')
    return jsonify({'message': 'Appointment updated successfully'})

@app.route('/appointments/<int:id>/reschedule', methods=['POST'])
@login_required
def reschedule_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    if current_user.role != 'student' or appointment.student_id != current_user.id:
        return jsonify({'message': 'Forbidden'}), 403
    data = request.json
    new_date = data.get('date')
    new_time = data.get('time')
    if is_past(new_date, new_time):
        return jsonify({'message': 'Cannot reschedule to a past time'}), 400
    doctor = get_available_doctor(appointment.specialization, new_date, new_time)
    if doctor is None:
        return jsonify({'message': 'No available doctor for the selected slot'}), 400
    hist = AppointmentChangeHistory(appointment_id=appointment.id, old_date=appointment.appointment_date, old_time=appointment.appointment_time, new_date=new_date, new_time=new_time, changed_by_user_id=current_user.id)
    appointment.appointment_date = new_date
    appointment.appointment_time = new_time
    appointment.doctor_id = doctor.id
    db.session.add(hist)
    db.session.commit()
    
    # Notify student
    create_notification(appointment.student_id, f"Your appointment has been successfully rescheduled to {new_date} at {new_time} with Dr. {doctor.name}.", 'reschedule')
    
    # Notify doctor
    if doctor.user_id:
        create_notification(doctor.user_id, f"Appointment Rescheduled: Student {current_user.full_name} has moved their appointment to {new_date} at {new_time}.", 'reschedule')
        
    return jsonify({'message': 'Appointment rescheduled'})

@app.route('/medical_records', methods=['POST'])
@login_required
def add_medical_record():
    if current_user.role not in ['doctor', 'admin']:
        return jsonify({'message': 'Forbidden'}), 403
    data = request.json
    appointment_id = data.get('appointment_id')
    diagnosis = data.get('diagnosis')
    notes = data.get('notes')
    appointment = Appointment.query.get_or_404(appointment_id)
    doc = None
    if current_user.role == 'doctor':
        doc = Doctor.query.filter_by(user_id=current_user.id).first()
        if doc is None or appointment.doctor_id != doc.id:
            return jsonify({'message': 'Forbidden'}), 403
    doctor_id = appointment.doctor_id if appointment.doctor_id else (doc.id if doc else None)
    record = MedicalRecord(appointment_id=appointment.id, patient_id=appointment.student_id, doctor_id=doctor_id, diagnosis=diagnosis, notes=notes)
    db.session.add(record)
    db.session.commit()
    
    # Notify student about new medical record
    doc_name = appointment.doctor.name if appointment.doctor else "Medical Staff"
    create_notification(appointment.student_id, f"A new medical record has been added for your visit on {appointment.appointment_date} by Dr. {doc_name}. You can now view your diagnosis and issue history.", 'medical_record')
    
    return jsonify({'message': 'Record added', 'id': record.id}), 201

@app.route('/medical_records', methods=['GET'])
@login_required
def get_medical_records():
    if current_user.role == 'student':
        records = MedicalRecord.query.filter_by(patient_id=current_user.id).all()
    elif current_user.role == 'doctor':
        doc = Doctor.query.filter_by(user_id=current_user.id).first()
        if doc is None:
            records = []
        else:
            records = MedicalRecord.query.filter_by(doctor_id=doc.id).all()
    else:
        records = MedicalRecord.query.all()
    return jsonify([{'id': r.id, 'appointment_id': r.appointment_id, 'patient_id': r.patient_id, 'doctor_id': r.doctor_id, 'diagnosis': r.diagnosis, 'notes': r.notes, 'created_at': r.created_at.isoformat()} for r in records])

@app.route('/prescriptions', methods=['POST'])
@login_required
def add_prescription():
    if current_user.role not in ['doctor', 'admin']:
        return jsonify({'message': 'Forbidden'}), 403
    data = request.json
    record_id = data.get('record_id')
    medication = data.get('medication')
    dosage = data.get('dosage')
    instructions = data.get('instructions')
    record = MedicalRecord.query.get_or_404(record_id)
    if current_user.role == 'doctor':
        doc = Doctor.query.filter_by(user_id=current_user.id).first()
        if doc is None or record.doctor_id != doc.id:
            return jsonify({'message': 'Forbidden'}), 403
    p = Prescription(record_id=record.id, medication=medication, dosage=dosage, instructions=instructions)
    db.session.add(p)
    db.session.commit()
    create_notification(record.patient_id, f"A new prescription has been issued for your recent visit (Record #{record.id}): {medication} ({dosage}). Please check your dashboard for full instructions.", 'prescription')
    return jsonify({'message': 'Prescription added', 'id': p.id}), 201

@app.route('/prescriptions', methods=['GET'])
@login_required
def get_prescriptions():
    if current_user.role == 'student':
        records = MedicalRecord.query.filter_by(patient_id=current_user.id).with_entities(MedicalRecord.id).all()
        record_ids = [r[0] for r in records]
        ps = Prescription.query.filter(Prescription.record_id.in_(record_ids)).all()
    elif current_user.role == 'doctor':
        doc = Doctor.query.filter_by(user_id=current_user.id).first()
        if doc is None:
            ps = []
        else:
            records = MedicalRecord.query.filter_by(doctor_id=doc.id).with_entities(MedicalRecord.id).all()
            record_ids = [r[0] for r in records]
            ps = Prescription.query.filter(Prescription.record_id.in_(record_ids)).all()
    else:
        ps = Prescription.query.all()
    return jsonify([{'id': x.id, 'record_id': x.record_id, 'medication': x.medication, 'dosage': x.dosage, 'instructions': x.instructions, 'created_at': x.created_at.isoformat()} for x in ps])

@app.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    ns = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return jsonify([{'id': n.id, 'content': n.content, 'type': n.type, 'is_read': n.is_read, 'created_at': n.created_at.isoformat()} for n in ns])

@app.route('/admin/students', methods=['GET'])
@login_required
def list_students_admin():
    if current_user.role != 'admin':
        return jsonify({'message': 'Forbidden'}), 403
    students = User.query.filter_by(role='student').all()
    return jsonify([{
        'id': s.id,
        'username': s.username,
        'email': s.email,
        'full_name': s.full_name
    } for s in students])

@app.route('/admin/students/<int:id>', methods=['DELETE'])
@login_required
def delete_student_admin(id):
    if current_user.role != 'admin':
        return jsonify({'message': 'Forbidden'}), 403
    student = User.query.get_or_404(id)
    if student.role != 'student':
        return jsonify({'message': 'Can only delete student accounts'}), 400
    
    # Delete associated data to satisfy foreign key constraints
    # 1. Delete notifications
    Notification.query.filter_by(user_id=student.id).delete()
    
    # 2. Find appointments to delete their records and prescriptions
    appointments = Appointment.query.filter_by(student_id=student.id).all()
    for appt in appointments:
        # Delete history
        AppointmentChangeHistory.query.filter_by(appointment_id=appt.id).delete()
        
        # Delete medical records and their prescriptions
        records = MedicalRecord.query.filter_by(appointment_id=appt.id).all()
        for rec in records:
            Prescription.query.filter_by(record_id=rec.id).delete()
            db.session.delete(rec)
        
        db.session.delete(appt)
    
    db.session.delete(student)
    db.session.commit()
    return jsonify({'message': 'Student account and all associated data deleted successfully'})

@app.route('/analytics/summary', methods=['GET'])
@login_required
def analytics_summary():
    if current_user.role != 'admin':
        return jsonify({'message': 'Forbidden'}), 403
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    q = Appointment.query
    if start_date:
        q = q.filter(Appointment.appointment_date >= start_date)
    if end_date:
        q = q.filter(Appointment.appointment_date <= end_date)
    total = q.count()
    status_counts = dict((s, 0) for s in ['Pending', 'Confirmed', 'Cancelled', 'Completed'])
    for s, c in db.session.query(Appointment.status, func.count(Appointment.id)).group_by(Appointment.status):
        status_counts[s] = c
    by_day = db.session.query(Appointment.appointment_date, func.count(Appointment.id)).group_by(Appointment.appointment_date).all()
    doctor_counts = db.session.query(Doctor.name, func.count(Appointment.id)).join(Appointment, Appointment.doctor_id == Doctor.id).group_by(Doctor.id).all()
    return jsonify({
        'total': total,
        'status_counts': status_counts,
        'by_day': [{'date': d, 'count': c} for d, c in by_day],
        'busiest_doctors': [{'doctor': n, 'count': c} for n, c in doctor_counts]
    })

@app.route('/admin/export/appointments', methods=['GET'])
@login_required
def export_appointments():
    if current_user.role != 'admin':
        return jsonify({'message': 'Forbidden'}), 403
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Student', 'Doctor', 'Specialization', 'Date', 'Time', 'Status', 'Urgent'])
    for a in Appointment.query.all():
        writer.writerow([a.id, a.student.full_name, a.doctor.name if a.doctor else '', a.specialization, a.appointment_date, a.appointment_time, a.status, 'Yes' if a.urgent else 'No'])
    csv_data = output.getvalue()
    output.close()
    return Response(csv_data, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=appointments.csv'})

@app.route('/symptom_checker', methods=['POST'])
def symptom_checker():
    data = request.json
    symptoms = (data.get('symptoms') or '').lower()
    if any(k in symptoms for k in ['chest pain', 'palpitations', 'shortness of breath']):
        spec = 'Cardiologist'
    elif any(k in symptoms for k in ['rash', 'skin', 'itch']):
        spec = 'Dermatologist'
    elif any(k in symptoms for k in ['fever', 'cough', 'headache']):
        spec = 'General Physician'
    elif any(k in symptoms for k in ['child', 'pediatric']):
        spec = 'Pediatrician'
    else:
        spec = 'General Physician'
    return jsonify({'suggested_specialization': spec})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
