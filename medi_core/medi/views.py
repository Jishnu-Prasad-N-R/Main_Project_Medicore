import base64
from io import BytesIO
import qrcode
import logging
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import CreateView, TemplateView, DetailView, UpdateView
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Q, Max
from django.http import HttpResponse
from django.template.loader import render_to_string

from weasyprint import HTML

from .models import User, DoctorProfile, Appointment, PatientProfile, Prescription, Department
from .forms import PatientSignUpForm, DoctorSignUpForm, EmailLoginForm, AppointmentForm, PrescriptionForm, DoctorProfileUpdateForm
from .utils import SMSNotificationService

logger = logging.getLogger(__name__)

#CUSTOM SECURITY MIXINS

class PatientRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return hasattr(self.request.user, 'patient_profile')

class DoctorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return hasattr(self.request.user, 'doctor_profile') and self.request.user.doctor_profile.is_verified

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


#1. HOME & SEARCH VIEW

class HomeView(TemplateView):
    template_name = 'medi/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctors = DoctorProfile.objects.filter(is_verified=True)
        query = self.request.GET.get('q')
        
        if query:
            doctors = doctors.filter(
                Q(specialization__name__icontains=query) |
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(address__icontains=query)
            )
            
        context['doctors'] = doctors
        return context


#2. REGISTRATION VIEWS

class PatientSignUpView(CreateView):
    model = User
    form_class = PatientSignUpForm
    template_name = 'registration/signup_patient.html'

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('home')

class DoctorSignUpView(CreateView):
    model = User
    form_class = DoctorSignUpForm
    template_name = 'registration/signup_doctor.html'

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Registration successful! Please wait for admin verification before logging in.")
        return redirect('login')


#3. LOGIN VIEW WITH VERIFICATION LOGIC

class CustomLoginView(LoginView):
    form_class = EmailLoginForm
    template_name = 'registration/login.html'

    def form_valid(self, form):
        user = form.get_user()
        
        if getattr(user, 'is_doctor', False):
            if not user.doctor_profile.is_verified:
                messages.error(self.request, "Your account is pending admin verification. Please try again later.")
                return redirect('login')
        
        login(self.request, user)
        return redirect(self.get_success_url())

    def get_success_url(self):
        user = self.request.user
        if user.is_superuser: 
            return '/admin-dashboard/' 
        elif getattr(user, 'is_doctor', False): 
            return '/doctor-dashboard/' 
        elif getattr(user, 'is_patient', False): 
            return '/patient-dashboard/'
        return '/' 


#4. PATIENT DASHBOARD

class PatientDashboardView(PatientRequiredMixin, TemplateView):
    template_name = 'patient/patient_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appointments'] = Appointment.objects.filter(
            patient=self.request.user.patient_profile
        ).order_by('-date')
        return context


#5. DOCTOR DASHBOARD & PROFILE

class DoctorDashboardView(DoctorRequiredMixin, TemplateView):
    template_name = 'doctor/doctor_dashboard.html' 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor_profile = self.request.user.doctor_profile
        today = date.today() 
        
        context['pending_appointments'] = Appointment.objects.filter(
            doctor=doctor_profile, status='Pending'
        ).order_by('date', 'time')

        context['today_appointments'] = Appointment.objects.filter(
            doctor=doctor_profile, status='Confirmed', date=today
        ).order_by('token_number', 'time')

        context['future_appointments'] = Appointment.objects.filter(
            doctor=doctor_profile, status='Confirmed', date__gt=today
        ).order_by('date', 'time')
            
        return context

class DoctorProfileUpdateView(DoctorRequiredMixin, UpdateView):
    model = DoctorProfile
    form_class = DoctorProfileUpdateForm
    template_name = 'doctor/doctor_edit_profile.html'
    success_url = reverse_lazy('doctor_dashboard')

    def get_object(self):
        return self.request.user.doctor_profile    


#6. BOOKING & APPOINTMENT STATUS

class BookAppointmentView(PatientRequiredMixin, CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'patient/book_appointment.html'
    success_url = reverse_lazy('patient_dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doctor'] = get_object_or_404(DoctorProfile, id=self.kwargs.get('doctor_id'))
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['doctor'] = get_object_or_404(DoctorProfile, id=self.kwargs.get('doctor_id'))
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        form.instance.patient = self.request.user.patient_profile
        form.instance.doctor = get_object_or_404(DoctorProfile, id=self.kwargs.get('doctor_id'))
        form.instance.status = 'Pending'
        try:
            return super().form_valid(form)
        except IntegrityError:
            form.add_error(None, "This slot was just claimed by another patient. Please choose another slot.")
            return self.form_invalid(form)

class UpdateAppointmentStatusView(DoctorRequiredMixin, View):
    def post(self, request, appointment_id):
        action = request.POST.get('action')
        
        with transaction.atomic():
            appointment = get_object_or_404(
                Appointment.objects.select_for_update(), 
                id=appointment_id, 
                doctor=request.user.doctor_profile
            )

            if appointment.status != 'Pending':
                return redirect('doctor_dashboard')

            if action == 'accept':
                doctor = DoctorProfile.objects.select_for_update().get(id=appointment.doctor.id)
                last_token_dict = Appointment.objects.filter(
                    doctor=doctor, date=appointment.date
                ).aggregate(Max('token_number'))
                
                appointment.status = 'Confirmed'
                appointment.token_number = (last_token_dict['token_number__max'] or 0) + 1
                appointment.save()

                try:
                    sms = SMSNotificationService()
                    sms.send_booking_confirmation(appointment)
                except Exception as e:
                    logger.exception(f"Failed to send SMS for Appointment {appointment.id}: {e}")

            elif action == 'reject':
                appointment.status = 'Cancelled'
                appointment.token_number = None
                appointment.save()
        
        return redirect('doctor_dashboard')


#7. PRESCRIPTION MANAGEMENT

class AddPrescriptionView(DoctorRequiredMixin, CreateView):
    model = Prescription
    form_class = PrescriptionForm
    template_name = 'doctor/add_prescription.html'
    success_url = reverse_lazy('doctor_dashboard')

    def dispatch(self, request, *args, **kwargs):
        self.appointment = get_object_or_404(Appointment, id=self.kwargs['appointment_id'])
        if request.user.doctor_profile != self.appointment.doctor:
            raise PermissionDenied("You can only prescribe for your own patients.")
        if self.appointment.date > date.today() or self.appointment.status != 'Confirmed':
             return redirect('doctor_dashboard')
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        form.instance.appointment = self.appointment
        response = super().form_valid(form)
        self.appointment.status = 'Completed'
        self.appointment.save()
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appointment'] = self.appointment
        return context

class ViewPrescriptionView(LoginRequiredMixin, DetailView):
    model = Prescription
    template_name = 'patient/view_prescription.html'
    context_object_name = 'prescription'
    slug_field = 'public_id'
    slug_url_kwarg = 'public_id'

    def get_object(self, queryset=None):
        prescription = super().get_object(queryset)
        user = self.request.user
        if user.is_superuser: 
            return prescription
        if hasattr(user, 'patient_profile') and prescription.appointment.patient == user.patient_profile: 
            return prescription
        if hasattr(user, 'doctor_profile') and prescription.appointment.doctor == user.doctor_profile: 
            return prescription
        raise PermissionDenied("Unauthorized access.")

class PatientMedicalHistoryView(DoctorRequiredMixin, TemplateView):
    template_name = 'doctor/patient_history.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = get_object_or_404(PatientProfile, id=self.kwargs['patient_id'])
        doctor = self.request.user.doctor_profile
        
        has_treated = Appointment.objects.filter(patient=patient, doctor=doctor).exists()
        
        if not has_treated:
            raise PermissionDenied("You can only view history for patients you are treating.")

        history = Appointment.objects.filter(
            patient=patient, status='Completed'
        ).order_by('-date')

        context['patient'] = patient
        context['history'] = history
        return context


#8. PDF GENERATOR (WEASYPRINT)

class DownloadPrescriptionView(LoginRequiredMixin, View):
    def get(self, request, public_id):
        prescription = get_object_or_404(Prescription, public_id=public_id)
        user = request.user
        
        is_patient = hasattr(user, 'patient_profile') and prescription.appointment.patient == user.patient_profile
        is_doctor = hasattr(user, 'doctor_profile') and prescription.appointment.doctor == user.doctor_profile
        
        if not (is_patient or is_doctor or user.is_superuser):
            raise PermissionDenied("Unauthorized access.")
            
        appointment = prescription.appointment
        verification_url = request.build_absolute_uri(reverse('view_prescription', args=[public_id]))
        
        qr = qrcode.QRCode(version=1, box_size=5, border=0)
        qr.add_data(verification_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        context = {
            'prescription': prescription,
            'doctor': appointment.doctor,
            'patient': appointment.patient,
            'qr_code_data': qr_base64
        }
        
        html_string = render_to_string('doctor/pdf_template.html', context)
        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
        
        response = HttpResponse(pdf_file, content_type='application/pdf')
        filename = f'Rx_{appointment.patient.user.first_name}_{appointment.date}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response


#9. CUSTOM ADMIN VIEWS

class CustomAdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name = 'custom_admin/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_patients'] = PatientProfile.objects.count()
        context['total_doctors'] = DoctorProfile.objects.count()
        context['total_appointments'] = Appointment.objects.count()
        context['pending_doctors'] = DoctorProfile.objects.filter(is_verified=False)
        return context

class VerifyDoctorView(AdminRequiredMixin, View):
    def post(self, request, doctor_id):
        action = request.POST.get('action')
        doctor = get_object_or_404(DoctorProfile, id=doctor_id)
        
        if action == 'approve':
            doctor.is_verified = True
            doctor.save()
        elif action == 'reject':
            doctor.user.is_active = False
            doctor.user.save()
            doctor.is_verified = False
            doctor.save()
            
        return redirect('custom_admin_dashboard')

class ManageDepartmentsView(AdminRequiredMixin, CreateView):
    model = Department
    fields = ['name', 'description']
    template_name = 'custom_admin/manage_departments.html'
    success_url = reverse_lazy('manage_departments')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.all()
        return context

class DeleteDepartmentView(AdminRequiredMixin, View):
    def post(self, request, dept_id):
        dept = get_object_or_404(Department, id=dept_id)
        dept.delete()
        return redirect('manage_departments')