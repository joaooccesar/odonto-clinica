from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
@admin.register(User)
class ClinicUserAdmin(UserAdmin):
    fieldsets=UserAdmin.fieldsets+(('Clínica',{'fields':('role',)}),)
    add_fieldsets=UserAdmin.add_fieldsets+(('Clínica',{'fields':('role',)}),)
