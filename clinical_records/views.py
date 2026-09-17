from pathlib import Path
from django.shortcuts import render,redirect,get_object_or_404
from django.http import FileResponse
from django.core.exceptions import ValidationError,PermissionDenied
from accounts.permissions import require,allowed
from patients.models import Patient
from professionals.models import Professional
from core.forms import ClinicalForm,AttachmentForm
from core.views import form_error
from audit.services import record
from .models import ClinicalEntry,Attachment
@require('clinical')
def add(request,pk):
    p=get_object_or_404(Patient,pk=pk)
    form=ClinicalForm(request.POST or None,instance=ClinicalEntry(patient=p,actor=request.user),initial={'kind':'tooth' if request.GET.get('tooth') else 'evolution','tooth':request.GET.get('tooth',''),'supersedes':request.GET.get('supersedes') if request.GET.get('supersedes','').isdigit() else None})
    form.fields['supersedes'].queryset=p.clinical_entries.all()
    if request.user.role=='dentist' and not request.user.is_manager:form.fields['professional'].queryset=Professional.objects.filter(user=request.user)
    if request.method=='POST' and form.is_valid():
        try:form.save();return redirect('patient_detail',pk=pk)
        except ValidationError as e:form_error(form,e)
    return render(request,'core/form.html',{'title':'Novo registro · '+p.name,'form':form,'back':f'/pacientes/{pk}/','hint':'Registros são preservados. Corrija um registro criando uma retificação vinculada ao original.'})
@require('dashboard')
def upload(request,pk):
    if not(allowed(request.user,'patients') or allowed(request.user,'finance')):raise PermissionDenied
    p=get_object_or_404(Patient,pk=pk)
    if request.user.role=='finance' and not p.entries.exists():raise PermissionDenied
    form=AttachmentForm(request.POST or None,request.FILES or None,instance=Attachment(patient=p,actor=request.user))
    if not allowed(request.user,'clinical'):
        form.fields['category'].choices=[('receipt','Comprovante')] if request.user.role=='finance' else [('receipt','Comprovante'),('document','Administrativo')]
    back=f'/pacientes/{pk}/' if allowed(request.user,'patients') else '/cadastros/lancamentos/'
    if request.method=='POST' and form.is_valid():form.save();return redirect(back)
    return render(request,'core/form.html',{'title':'Anexar documento · '+p.name,'form':form,'multipart':True,'back':back,'hint':'PDF, JPG ou PNG, até 10 MB. Arquivos criptografados e acessíveis conforme seu perfil.'})
@require('dashboard')
def download(request,pk):
    item=get_object_or_404(Attachment,pk=pk)
    if item.category=='clinical':
        if not allowed(request.user,'clinical'):raise PermissionDenied
    elif not(allowed(request.user,'patients') or (allowed(request.user,'finance') and item.category=='receipt')):raise PermissionDenied
    record('download_attachment',item)
    response=FileResponse(item.file.open('rb'),as_attachment=True,filename=f'documento-{item.pk}{Path(item.file.name).suffix}');response['Cache-Control']='no-store';return response
@require('clinical')
def document(request,pk):
    entry=get_object_or_404(ClinicalEntry.objects.select_related('patient','professional','actor'),pk=pk);record('print_clinical',entry)
    return render(request,'clinical_records/document.html',{'entry':entry})
