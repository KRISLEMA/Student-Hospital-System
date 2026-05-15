# 🏥 JKUAT Student Hospital Appointment Management System

A web-based hospital appointment management system developed for **Jomo Kenyatta University of Agriculture and Technology (JKUAT)** University Hospital. The system digitizes and streamlines the medical appointment scheduling process, enabling students to book appointments online while giving hospital staff and administrators tools to manage schedules and patient flow efficiently.

> **Author:** Shadrack Lemayian (SCT222-0757/2021)  
> **Supervisor:** Mr. Mark Brian Muiruri  
> **Institution:** Department of Information Technology, School of Computing and Information Technology, JKUAT  
> **Year:** 2026

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Role-Based Access Control](#role-based-access-control)
- [Installation & Setup](#installation--setup)
- [Usage Guide](#usage-guide)
- [Database Schema](#database-schema)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Limitations](#limitations)
- [Future Improvements](#future-improvements)
- [License](#license)

---

## Overview

JKUAT students seeking medical attention were previously required to physically visit the hospital to book appointments or wait on a walk-in basis, causing long queues, double-bookings, missed lectures, and poor resource utilization.

This system replaces the manual process with a centralized digital platform that:

- Allows **students** to book, reschedule, and cancel appointments online
- Gives **medical staff** a clear view of daily schedules and appointment statuses
- Provides **administrators** with tools to manage doctors, availability slots, and generate reports

---

## Features

### 👨‍🎓 Student (Patient)
- Register using JKUAT registration number and email
- Book appointments by selecting department, doctor, date, and time slot
- View upcoming and past appointment history
- Reschedule or cancel appointments (cancellation allowed ≥ 2 hours before scheduled time)
- Receive email confirmations and 24-hour reminders

### 🩺 Doctor (Medical Staff)
- View daily and weekly appointment schedules
- Update appointment statuses: `Attended`, `Missed`, or `Cancelled`
- Access student appointment details per session

### 🛠️ Administrator
- Add, edit, and remove doctor profiles
- Set and manage doctor availability (working days and time slots)
- Block time slots for meetings or leave
- Generate daily, weekly, and monthly appointment reports
- Export reports as **PDF** or **CSV**

### 🔒 Security
- Password hashing using **bcrypt**
- Role-Based Access Control (RBAC) — three roles: `student`, `staff`, `administrator`
- Protection against SQL injection via prepared statements / ORM queries
- HTTPS enforcement
- Session timeout after 30 minutes of inactivity

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.x |
| **Backend Framework** | Django / Flask |
| **Frontend** | HTML5, CSS3, JavaScript, Bootstrap 5 |
| **Database** | MySQL / PostgreSQL |
| **Email Notifications** | SMTP (Django's email backend / smtplib) |
| **PDF Export** | ReportLab / WeasyPrint |
| **Version Control** | Git & GitHub |
| **Development Server** | Django Dev Server / Gunicorn |
| **Web Server** | Apache / Nginx (production) |

---

## System Architecture

The system follows a **three-tier client-server architecture**:

```
┌──────────────────────────────────────────────────┐
│              Presentation Tier (Frontend)         │
│         HTML5 · CSS3 · JavaScript · Bootstrap 5  │
└─────────────────────┬────────────────────────────┘
                      │ HTTP/HTTPS
┌─────────────────────▼────────────────────────────┐
│              Application Tier (Backend)           │
│   Python (Django/Flask) · Business Logic ·        │
│   Authentication · Appointment Processing ·       │
│   Notifications · Report Generation              │
└─────────────────────┬────────────────────────────┘
                      │ ORM / SQL Queries
┌─────────────────────▼────────────────────────────┐
│                Data Tier (Database)               │
│          MySQL / PostgreSQL · Appointment         │
│          Records · User Accounts · Audit Logs     │
└──────────────────────────────────────────────────┘
```

---

## Role-Based Access Control

| Feature | Student | Medical Staff | Administrator |
|---|:---:|:---:|:---:|
| Register / Login | ✅ | ✅ | ✅ |
| Book Appointment | ✅ | ❌ | ❌ |
| View Own Appointments | ✅ | ❌ | ❌ |
| Reschedule / Cancel Appointment | ✅ | ❌ | ❌ |
| View Daily Schedule | ❌ | ✅ | ✅ |
| Update Appointment Status | ❌ | ✅ | ✅ |
| Manage Doctor Profiles | ❌ | ❌ | ✅ |
| Set Doctor Availability | ❌ | ❌ | ✅ |
| Block Time Slots | ❌ | ❌ | ✅ |
| Generate & Export Reports | ❌ | ❌ | ✅ |

---

## Installation & Setup

### Prerequisites

- Python 3.10+
- pip
- MySQL or PostgreSQL
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/hospital-ams.git
cd hospital-ams
```

### 2. Create and Activate a Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Database

Create a new database:

```sql
CREATE DATABASE hospital_ams;
```

Update your database settings in `config/settings.py` (Django) or `.env`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # or postgresql
        'NAME': 'hospital_ams',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### 5. Apply Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Seed Initial Data (Optional)

```bash
python manage.py loaddata fixtures/initial_data.json
```

### 7. Configure Email Notifications

In `settings.py`, configure your SMTP credentials:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your_email@gmail.com'
EMAIL_HOST_PASSWORD = 'your_app_password'
```

### 8. Run the Development Server

```bash
python manage.py runserver
```

Access the system at: [http://localhost:8000](http://localhost:8000)

### 9. Create a Superuser (Admin)

```bash
python manage.py createsuperuser
```

---

## Usage Guide

### Student

1. Navigate to the home page and click **Register**
2. Fill in your full name, JKUAT registration number (format: `SCT222-XXXX/YYYY`), email, and password
3. Log in and click **Book Appointment** from the dashboard
4. Select a service department, doctor, date, and available time slot
5. Click **Confirm Booking** — a confirmation email will be sent
6. Manage your bookings under **My Appointments** (reschedule or cancel as needed)

### Medical Staff

1. Log in with your staff credentials
2. Your **daily schedule** is displayed on the dashboard
3. Click any appointment to view student details and update the status:
   - `Attended` · `Missed` · `Cancelled`
4. Use the **calendar view** for a weekly overview

### Administrator

1. Log in with administrator credentials
2. Use **Doctor Management** to add, edit, or remove doctor profiles
3. Use **Schedule Management** to define weekly availability or block time slots
4. Use **Reports** to generate and export appointment summaries (PDF / CSV)

---

## Database Schema

Key entities and their relationships:

```
users
 ├── id, name, email, password_hash, role, registration_number, created_at

doctors
 ├── id, name, department, specialization, email, is_active

availability
 ├── id, doctor_id (FK), day_of_week, start_time, end_time, is_blocked

appointments
 ├── id, student_id (FK), doctor_id (FK), appt_date, time_slot,
 │   service_type, status [booked|attended|missed|cancelled], created_at

notifications
 ├── id, user_id (FK), appointment_id (FK), type, sent_at, status

reports
 └── generated on-the-fly from appointments table with filters
```

---

## Testing

The system was validated using the following testing strategies:

| Strategy | Description |
|---|---|
| **Unit Testing** | Individual functions tested in isolation (hashing, validation, double-booking logic) |
| **Integration Testing** | Modules combined and tested together (booking ↔ availability ↔ notifications) |
| **Functional / Black-Box Testing** | System tested from the user's perspective against all functional requirements |
| **Usability Testing** | 5 students + 2 staff completed tasks; average satisfaction score: **4.3 / 5** |
| **Performance Testing** | Simulated 200 users and 500 records; all pages loaded within **3 seconds** |
| **Security Testing** | SQL injection attempts blocked; session timeouts verified; HTTPS enforced |
| **Smoke Testing** | Core functions verified before each testing phase |

### Running Tests

```bash
python manage.py test
```

### Test Coverage Summary

| Module | Test Cases | Status |
|---|:---:|:---:|
| User Authentication | TC01–TC04 | ✅ All Pass |
| Appointment Booking | TC05–TC08 | ✅ All Pass |
| Appointment Management | TC09–TC12 | ✅ All Pass |
| Schedule Management | TC13–TC16 | ✅ All Pass |
| Reporting | TC17–TC18 | ✅ All Pass |
| Security | TC19–TC20 | ✅ All Pass |

**Total: 20/20 test cases passed**

---

## Project Structure

```
hospital-ams/
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── authentication/       # Registration, login, session management
│   ├── appointments/         # Booking, rescheduling, cancellation
│   ├── schedules/            # Doctor availability, slot management
│   ├── reports/              # Report generation and export
│   └── notifications/        # Email notifications and reminders
├── templates/
│   ├── base.html
│   ├── auth/
│   ├── student/
│   ├── staff/
│   └── admin/
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── fixtures/
│   └── initial_data.json
├── requirements.txt
├── manage.py
└── README.md
```

---

## Limitations

- The system was developed and tested using **simulated data** rather than real JKUAT hospital records (due to ethical restrictions on patient data access)
- **SMS notifications** were not implemented due to SMS API costs; email notifications are used instead
- Performance testing was conducted on a **local server** — real-world cloud performance may vary
- Real-time slot updates require AJAX/WebSocket implementation (currently uses page refresh)
- Deployment was limited to a **localhost environment** due to budget constraints

---

## Future Improvements

- ☁️ **Cloud Deployment** — Host on AWS, Google Cloud, or a shared server at `hospital.jkuat.ac.ke`
- 📱 **SMS Notifications** — Integrate Africa's Talking SMS gateway for local Kenyan networks
- ⚡ **Real-Time Slot Updates** — AJAX-based dynamic slot loading without full page reload
- 🔗 **JKUAT Portal Integration** — Authenticate students using existing JKUAT credentials (SSO)
- 📲 **Mobile Application** — Android and iOS companion app for wider accessibility
- 📊 **Data Analytics Dashboard** — Visual charts for appointment trends and service demand
- 🎥 **Telemedicine Module** — Remote video consultations for minor health concerns

---

## Ethical Statement

This system was developed strictly for academic purposes. No real patient medical records were accessed or stored during development or testing. All test data used is simulated and non-identifiable. User privacy, confidentiality, and data security are prioritized throughout the system design.

---

## License

This project is submitted in partial fulfillment of the requirements for the degree of **Bachelor of Science in Business Computing** at Jomo Kenyatta University of Agriculture and Technology (JKUAT). All rights reserved © 2026 Shadrack Lemayian.