# MediCore - Smart Healthcare Management System

MediCore is a secure, role-based web application built with **Django** that bridges the gap between patients and medical professionals. It streamlines clinic operations, handles smart appointment scheduling, prevents double-booking race conditions, and provides secure Electronic Medical Record (EMR) management with cryptographic PDF prescriptions.

## Key Features

### Role-Based Access Control (RBAC)
The system strictly segregates functionality using custom Django Mixins (`DoctorRequiredMixin`, `PatientRequiredMixin`, `AdminRequiredMixin`):
* **System Admin:** Verifies newly registered doctors, manages medical departments, and views overarching clinic statistics via a custom Admin Control Panel.
* **Doctors:** Access a dedicated dashboard to approve/reject pending appointments, view daily schedules, access patient medical histories, and generate digital prescriptions.
* **Patients:** Can search for specialists, book appointments within clinic hours, view appointment statuses, and download past prescriptions as PDFs.

### Smart Appointment Scheduling
* **Validation:** Patients can only book within designated clinic hours (10:00 AM - 6:00 PM) and cannot book past dates or Sundays.
* **Race Condition Prevention:** Implemented database-level `UniqueConstraints` and atomic transactions to guarantee that two patients cannot book the same doctor at the exact same time.

### Digital Prescriptions & PDF Rendering
* Doctors can generate detailed clinical reports including vitals, diagnosis, and Rx details.
* Utilizes **WeasyPrint** to perform server-side HTML-to-PDF rendering, allowing patients to download perfectly formatted A4 prescriptions.
* Includes a dynamically generated **QR Code** on the PDF for easy digital verification.

### Automated SMS Alerts (Twilio)
* Integrates the **Twilio REST API** to send real-time text message notifications when a doctor confirms a patient's appointment.
* **Presentation/Demo Bypass:** Features a custom routing mechanism that sends all SMS alerts to a verified developer phone number, bypassing fake patient numbers during live portfolio demonstrations.

### Security Highlights
* **IDOR Protection:** Medical records and prescription URLs are secured using Universally Unique Identifiers (UUIDs) (`public_id`) instead of sequential primary keys, preventing Insecure Direct Object Reference vulnerabilities.
* **Data Isolation:** Doctors can only view the medical history of patients they have actively treated.
* **Graceful State Handling:** Optimized backend database queries to securely handle and visually present empty data states (e.g., new patients with no medical history) without throwing unauthorized server errors.

## Technology Stack

**Backend:**
* Python 3.x
* Django (Web Framework)
* SQLite3 (Database)

**Frontend:**
* HTML5, CSS3
* Bootstrap 5 (Responsive UI)
* jQuery, Owl Carousel (Sliders), Tempus Dominus (Date/Time Pickers)

**Third-Party APIs & Libraries:**
* `twilio` (SMS Notifications)
* `weasyprint` (PDF Generation)
* `qrcode` (QR Code Generation)
* `python-decouple` (Environment Variable Management)

## Local Setup & Installation

Follow these steps to get the project running on your local machine.

**1. Clone the repository**
```bash
git clone https://github.com/yourusername/medicore.git
cd medicore
```

**2. Create and activate a virtual environment**
```bash
python -m venv env

# On Windows:
env\Scripts\activate
# On Mac/Linux:
source env/bin/activate
```

**3. Install Dependencies**
```bash
python -m pip install -r requirements.txt
```
*(Note: If `weasyprint` fails to install on Windows, ensure you have the GTK3 runtime installed).*

**4. Configure Environment Variables**
Create a `.env` file in the root directory (next to `manage.py`) and add your configuration:
```text
SECRET_KEY=your_django_secret_key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Twilio Credentials
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_SENDER=+1234567890

# Presentation Bypass (Routes all SMS to this number)
MY_NUMBER=+19876543210
```

**5. Run Database Migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

**6. Create a Superuser**
You need an admin account to create departments and verify doctor registrations.
```bash
python manage.py createsuperuser
```

**7. Run the Application**
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

## Project Structure Overview

```text
MediCore/
├── medi_core/               # Django Project Settings
│   ├── settings.py          # Core settings & decoupling
│   └── urls.py              # Root URL routing
├── medi/                    # Main Application App
│   ├── models.py            # Database schema (User, Profiles, Appointments, etc.)
│   ├── views.py             # Business logic & Class-Based Views
│   ├── forms.py             # Form validation & custom logic
│   └── utils.py             # Twilio SMS Service class
├── static/                  # CSS, JS, Images, and Vendor libraries
├── templates/               # HTML templates (Bootstrap 5)
└── manage.py                # Django execution script
```

## Author

**Jishnu Prasad**
*Built as a comprehensive portfolio project demonstrating full-stack Django capabilities, REST API integration, and secure database design.*