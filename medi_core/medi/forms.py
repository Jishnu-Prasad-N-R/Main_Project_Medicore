from django import forms
from django.db import transaction
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from datetime import time

from .models import User, DoctorProfile, PatientProfile, Appointment, Prescription, Department

# --- Custom Login Form ---
class EmailLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Email Address"
        self.fields['username'].widget.attrs.update({
            'class': 'form-control bg-light border-0',
            'style': 'height: 55px;',
            'placeholder': 'Enter your Email'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control bg-light border-0',
            'style': 'height: 55px;',
            'placeholder': 'Password'
        })

# --- Styling Helper ---
class MediCoreFormStyle(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            label = self.fields[field].label
            if not label:
                label = field.replace("_", " ").title()
            
            self.fields[field].widget.attrs.update({
                'class': 'form-control bg-light border-0', 
                'style': 'height: 55px;',
                'placeholder': label 
            })

# Custom Widget for Date
class DateInput(forms.DateInput):
    input_type = 'date'

# --- Patient Sign Up Form ---
class PatientSignUpForm(MediCoreFormStyle):
    first_name = forms.CharField(label="First Name", required=True)
    last_name = forms.CharField(label="Last Name", required=True)
    email = forms.EmailField(label="Email Address", required=True)
    password = forms.CharField(widget=forms.PasswordInput(), label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput(), label="Confirm Password")


    date_of_birth = forms.DateField(
        label="Date of Birth", 
        widget=DateInput(attrs={'class': 'form-control bg-light border-0', 'style': 'height: 55px;'}),
        required=True
    )
    
    gender = forms.ChoiceField(
        label="Gender",
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
        widget=forms.Select(attrs={'class': 'form-control bg-light border-0', 'style': 'height: 55px;'})
    )
    blood_group = forms.ChoiceField(
        label="Blood Group",
        choices=[('', 'Select Blood Group'), ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'), ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control bg-light border-0', 'style': 'height: 55px;'})
    )
    phone_number = forms.CharField(label="Phone Number", required=True)
    known_allergies = forms.CharField(label="Known Allergies (Optional)", required=False)
    address = forms.CharField(label="Home Address", widget=forms.Textarea(attrs={'rows': 3, 'style': 'height: auto;'}))

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match!")

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.set_password(self.cleaned_data['password'])
        user.is_patient = True
        
        if commit:
            user.save()
            PatientProfile.objects.create(
                user=user,
                date_of_birth=self.cleaned_data.get('date_of_birth'), # Save DOB
                gender=self.cleaned_data.get('gender'),
                blood_group=self.cleaned_data.get('blood_group'),
                phone_number=self.cleaned_data.get('phone_number'),
                known_allergies=self.cleaned_data.get('known_allergies'),
                address=self.cleaned_data.get('address')
            )
        return user

# --- Doctor Sign Up Form ---
class DoctorSignUpForm(MediCoreFormStyle):
    first_name = forms.CharField(label="First Name", required=True)
    last_name = forms.CharField(label="Last Name", required=True)
    email = forms.EmailField(label="Email Address", required=True)
    password = forms.CharField(widget=forms.PasswordInput(), label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput(), label="Confirm Password")

    specialization = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        label="Department / Specialization",
        empty_label="Select Department",
        widget=forms.Select(attrs={'class': 'form-control bg-light border-0', 'style': 'height: 55px;'})
    )
    
    qualifications = forms.CharField(
        label="Degrees / Qualifications (e.g. MBBS, MD)", 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. MBBS, MD, MS'})
    )
    
    registration_number = forms.CharField(label="Medical Reg. Number", required=True)
    phone_number = forms.CharField(label="Contact Number", required=True)
    profile_pic = forms.ImageField(label="Profile Photo", required=False) 
    address = forms.CharField(label="Clinic Address", widget=forms.Textarea(attrs={'rows': 3}))

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match!")

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.set_password(self.cleaned_data['password'])
        user.is_doctor = True
        
        if commit:
            user.save()
            DoctorProfile.objects.create(
                user=user,
                specialization=self.cleaned_data.get('specialization'),
                qualifications=self.cleaned_data.get('qualifications'), # SAVE THE NEW FIELD
                registration_number=self.cleaned_data.get('registration_number'), 
                phone_number=self.cleaned_data.get('phone_number'),
                address=self.cleaned_data.get('address'),
                profile_pic=self.cleaned_data.get('profile_pic'),
                is_verified=False 
            )
        return user


class DoctorProfileUpdateForm(MediCoreFormStyle):
    class Meta:
        model = DoctorProfile
        
        fields = ['qualifications', 'phone_number', 'address', 'profile_pic']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['address'].help_text = "Keep this updated so patients can find your clinic."

class TimeInput(forms.TimeInput):
    input_type = 'time'
 

class AppointmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Appointment
        fields = ['date', 'time', 'reason']
        widgets = {
            'date': DateInput(attrs={'class': 'form-control bg-light border-0', 'style': 'height: 55px;'}),
            'time': TimeInput(attrs={'class': 'form-control bg-light border-0', 'style': 'height: 55px;'}),
            'reason': forms.Textarea(attrs={'class': 'form-control bg-light border-0', 'rows': 5, 'placeholder': 'Describe your problem'}),
        }

    # 2. The Logic: Check for Days, Time Boundaries, Interval Constraints, AND Double Booking
    def clean(self):
        cleaned_data = super().clean()
        date_val = cleaned_data.get('date')
        time_val = cleaned_data.get('time')

        if not date_val or not time_val:
            return cleaned_data

        local_today = timezone.localdate()
        local_now = timezone.localtime().time()

        if date_val < local_today:
            raise forms.ValidationError("You cannot book an appointment for a past date.")

        if date_val == local_today and time_val < local_now:
            raise forms.ValidationError("You cannot book a time slot that has already passed today.")

        if time_val.minute not in [0, 15, 30, 45]:
            raise forms.ValidationError("Appointments must be booked in 15-minute intervals (e.g., 10:00, 10:15).")

        if self.doctor:
            
            if date_val.weekday() == 6:
                raise forms.ValidationError(
                    "The clinic is closed on Sundays. Please select a date from Monday to Saturday."
                )
            
            # --- NEW FEATURE 2: Restrict to Clinic Hours (10 AM to 6 PM) ---
            # time(hour, minute) in 24-hour format
            clinic_open = time(10, 0)  
            clinic_close = time(18, 0) 
            
            if not (clinic_open <= time_val <= clinic_close):
                raise forms.ValidationError(
                    "Appointments can only be booked during clinic hours: 10:00 AM to 6:00 PM."
                )

            # Check for Double Booking 
            booking_exists = Appointment.objects.filter(
                doctor=self.doctor,
                date=date_val,
                time=time_val
            ).exclude(status='Cancelled').exists()

            if booking_exists:
                raise forms.ValidationError(
                    "This exact time slot is already booked. Please select a different time."
                )
        
        return cleaned_data
        
class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['symptoms', 'medicine_details', 'notes', 'blood_pressure', 'sugar_level', 'cholesterol', 'weight']
        widgets = {
            'symptoms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'e.g., Fever, Cold'}),
            'medicine_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'e.g., Paracetamol 500mg - 1-0-1 after food'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Diet or other instructions'}),
            'blood_pressure': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '120/80'}),
            'sugar_level': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '90 mg/dL'}),
            'cholesterol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '200 mg/dL'}),
            'weight': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kg'}),
        }