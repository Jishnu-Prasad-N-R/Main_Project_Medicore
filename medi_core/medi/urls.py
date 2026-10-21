from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    # General URLs
    path('', views.HomeView.as_view(), name='home'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    
    # Registration URLs
    path('signup/patient/', views.PatientSignUpView.as_view(), name='signup_patient'),
    path('signup/doctor/', views.DoctorSignUpView.as_view(), name='signup_doctor'),
    
    # Patient URLs
    path('patient-dashboard/', views.PatientDashboardView.as_view(), name='patient_dashboard'),
    path('book-appointment/<int:doctor_id>/', views.BookAppointmentView.as_view(), name='book_appointment'),
    path('view-prescription/<uuid:public_id>/', views.ViewPrescriptionView.as_view(), name='view_prescription'),
    path('download-prescription/<uuid:public_id>/', views.DownloadPrescriptionView.as_view(), name='download_prescription'),
    
    # Doctor URLs
    path('doctor-dashboard/', views.DoctorDashboardView.as_view(), name='doctor_dashboard'),
    path('doctor/edit-profile/', views.DoctorProfileUpdateView.as_view(), name='edit_doctor_profile'),
    path('update-status/<int:appointment_id>/', views.UpdateAppointmentStatusView.as_view(), name='update_status'),
    path('add-prescription/<int:appointment_id>/', views.AddPrescriptionView.as_view(), name='add_prescription'),
    path('patient-history/<int:patient_id>/', views.PatientMedicalHistoryView.as_view(), name='patient_history'),
    
    # CUSTOM ADMIN URLS 
    path('admin-dashboard/', views.CustomAdminDashboardView.as_view(), name='custom_admin_dashboard'),
    path('verify-doctor/<int:doctor_id>/', views.VerifyDoctorView.as_view(), name='verify_doctor'),
    path('manage-departments/', views.ManageDepartmentsView.as_view(), name='manage_departments'),
    path('delete-department/<int:dept_id>/', views.DeleteDepartmentView.as_view(), name='delete_department'),
]