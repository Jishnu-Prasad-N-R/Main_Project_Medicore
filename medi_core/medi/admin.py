from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, DoctorProfile, PatientProfile, Appointment, Prescription

# 1. Register the User Model
# (We keep UserAdmin because it handles password hashing correctly in the admin panel)
admin.site.register(User, UserAdmin)

# 2. Custom Admin for DoctorProfile
class DoctorProfileAdmin(admin.ModelAdmin):

    list_display = ('doctor_name', 'specialization', 'phone_number', 'is_verified')
    
    list_filter = ('is_verified', 'specialization')
    
    search_fields = ('user__first_name', 'user__last_name', 'specialization', 'registration_number')
    
    list_editable = ('is_verified',)

    def doctor_name(self, obj):
        return f"Dr. {obj.user.first_name} {obj.user.last_name}"
    
    doctor_name.short_description = 'Doctor Name'

admin.site.register(DoctorProfile, DoctorProfileAdmin)

# 3. Register other models
admin.site.register(PatientProfile)
admin.site.register(Appointment)
admin.site.register(Prescription)