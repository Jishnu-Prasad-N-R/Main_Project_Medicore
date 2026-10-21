import uuid
from datetime import date 
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    is_patient = models.BooleanField(default=False)
    is_doctor = models.BooleanField(default=False)
    
    email = models.EmailField(unique=True, null=False, blank=False)

    def __str__(self):
        return self.email
    
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    
    specialization = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    
    qualifications = models.CharField(max_length=100, help_text="e.g. MBBS, MD, MS", default="MBBS")
    
    address = models.TextField()
    phone_number = models.CharField(max_length=15)
    profile_pic = models.ImageField(upload_to='profile_pics/', blank=True, null=True) 
    is_verified = models.BooleanField(default=False)
    
    registration_number = models.CharField(max_length=50, unique=True, help_text="Medical Council Registration Number")

    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name}"

class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    
    date_of_birth = models.DateField(null=True, blank=True)
    
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], default='Male')
    blood_group = models.CharField(max_length=5, choices=[('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'), ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-')], blank=True)
    
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    
    known_allergies = models.TextField(blank=True, null=True, help_text="e.g. Penicillin, Peanuts, Dust")

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
    @property
    def age(self):
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return 0

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='appointments')
    
    date = models.DateField()
    time = models.TimeField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    token_number = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['doctor', 'date', 'time'],
                condition=~Q(status='Cancelled'),
                name='unique_active_appointment_slot'
            )
        ]

    def __str__(self):
        return f"{self.patient.user.first_name} - {self.doctor.user.last_name}"
    
    @property
    def has_prescription(self):
        return hasattr(self, 'prescription')
    
class Prescription(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='prescription')
    
    symptoms = models.TextField()
    medicine_details = models.TextField(help_text="Enter medicine name, dosage, and frequency")
    notes = models.TextField(blank=True, null=True)
    
    blood_pressure = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. 120/80 mmHg")
    sugar_level = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. 140 mg/dL")
    cholesterol = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. 200 mg/dL")
    weight = models.CharField(max_length=20, blank=True, null=True, help_text="in Kg")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prescription for {self.appointment.patient.user.first_name}"