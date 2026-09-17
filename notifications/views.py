from urllib.parse import urlencode
from datetime import timedelta
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.utils import timezone
from accounts.permissions import require,allowed
from appointments.models import Appointment
from appointments.services import scope
from inventory.models import Product,Batch
from .models import Reminder
@require('notifications')
def index(request):
    appointments=[]
    if allowed(request.user,'appointments'):
        for a in scope(request.user).filter(start__gte=timezone.now(),start__lte=timezone.now()+timedelta(days=2)).exclude(status__in=['cancelled','missed','completed']).select_related('patient'):
            text=f'Olá, {a.patient.name}. Lembrete de consulta em {timezone.localtime(a.start):%d/%m/%Y às %H:%M}. Entre em contato para confirmar.'
            phone=''.join(x for x in a.patient.phone if x.isdigit())
            if len(phone) in [10,11]:phone='55'+phone
            appointments.append({'a':a,'whatsapp':'https://wa.me/'+phone+'?'+urlencode({'text':text}) if phone and a.patient.reminder_consent else ''})
    return render(request,'notifications/index.html',{'title':'Notificações','appointments':appointments,'low':[p for p in Product.objects.filter(active=True).prefetch_related('batches') if p.quantity<=p.minimum] if allowed(request.user,'inventory') else [],'expiry':Batch.objects.filter(quantity__gt=0,expiry__lte=timezone.localdate()+timedelta(days=30)) if allowed(request.user,'inventory') else []})
@require('appointments')
@require_POST
def email_reminder(request,pk):
    a=get_object_or_404(scope(request.user),pk=pk)
    if not a.patient.reminder_consent or not a.patient.email:messages.error(request,'E-mail e autorização de lembrete são necessários.');return redirect('/notificacoes/')
    try:
        send_mail('Lembrete de consulta',f'Sua consulta está agendada para {timezone.localtime(a.start):%d/%m/%Y às %H:%M}. Entre em contato para confirmar.',None,[a.patient.email],fail_silently=False)
        Reminder.objects.create(appointment=a,channel='email',status='sent',actor=request.user,sent_at=timezone.now());messages.success(request,'Lembrete encaminhado ao serviço de e-mail configurado.')
    except Exception:
        Reminder.objects.create(appointment=a,channel='email',status='error',actor=request.user,error='Falha de envio. Verifique configuração SMTP.');messages.error(request,'Falha no envio. Verifique o SMTP.')
    return redirect('/notificacoes/')
