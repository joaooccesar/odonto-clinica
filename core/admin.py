from django.apps import apps
from django.contrib import admin
class ReadOnly(admin.ModelAdmin):
    def has_add_permission(self,request):return False
    def has_change_permission(self,request,obj=None):return False
    def has_delete_permission(self,request,obj=None):return False
for label in ['patients','professionals','appointments','clinical_records','treatments','inventory','suppliers','purchases','finance','audit','notifications']:
    for model in apps.get_app_config(label).get_models():
        admin.site.register(model,ReadOnly)
admin.site.site_header='OdontoClínica · Administração técnica'
