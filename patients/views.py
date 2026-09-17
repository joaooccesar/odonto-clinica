from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from accounts.permissions import require,allowed
from audit.services import record
from .models import Patient
from .services import anonymize
@require('patients')
def detail(request,pk):
    p=get_object_or_404(Patient,pk=pk);record('view_patient',p)
    data={'title':p.name,'patient':p,'appointments':p.appointments.select_related('professional','procedure').order_by('-start')[:30],'plans':p.plans.select_related('professional').prefetch_related('items')}
    if allowed(request.user,'clinical'):
        data['records']=p.clinical_entries.select_related('professional','actor','supersedes')[:100];data['anamnesis']=p.clinical_entries.filter(kind='anamnesis').first();data['attachments']=p.attachments.all();teeth={}
        for entry in p.clinical_entries.exclude(tooth='').order_by('-created_at'):
            if entry.tooth not in teeth:teeth[entry.tooth]=entry
        arches=[[18,17,16,15,14,13,12,11,21,22,23,24,25,26,27,28],[48,47,46,45,44,43,42,41,31,32,33,34,35,36,37,38],[55,54,53,52,51,61,62,63,64,65],[85,84,83,82,81,71,72,73,74,75]]
        data['arches']=[[{'number':n,'condition':teeth[str(n)].condition if str(n) in teeth else 'unrecorded','label':teeth[str(n)].get_condition_display() if str(n) in teeth else 'Sem registro'} for n in row] for row in arches]
    else:data['attachments']=p.attachments.exclude(category='clinical')
    if allowed(request.user,'payments'):data['entries']=p.entries.filter(direction='in').prefetch_related('payments')
    return render(request,'patients/detail.html',data)
@require('settings')
@require_POST
def anonymize_view(request,pk):
    p=get_object_or_404(Patient,pk=pk)
    try:anonymize(p,request.user,request.POST.get('reason',''));messages.success(request,'Cadastro anonimizado.')
    except ValidationError as e:messages.error(request,' '.join(e.messages))
    return redirect('patient_detail',pk=pk)
