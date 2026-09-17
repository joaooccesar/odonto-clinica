import json
from datetime import datetime,date,time,timedelta
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db.models import Q
from accounts.permissions import require
from core.forms import AppointmentForm
from core.views import form_error,filter_context
from professionals.models import Room,Professional,ScheduleBlock
from reports.services import filter_appointments
from .models import Appointment
from .services import scope,save_appointment,reschedule,transition,TERMINAL
@require('appointments')
def calendar(request):return render(request,'appointments/calendar.html',{'title':'Agenda','rooms':Room.objects.filter(active=True),**filter_context()})
@require('appointments')
def form(request,pk=None):
    obj=get_object_or_404(scope(request.user),pk=pk) if pk else None
    initial={key:request.GET[key] for key in ['patient','professional','procedure','room','plan_item'] if request.GET.get(key,'').isdigit()}
    for key in ['start','end']:
        if request.GET.get(key):initial[key]=request.GET[key]
    frm=AppointmentForm(request.POST or None,instance=obj,initial=initial)
    if request.user.role=='dentist' and not request.user.is_manager:
        frm.fields['professional'].queryset=Professional.objects.filter(user=request.user);frm.fields['plan_item'].queryset=frm.fields['plan_item'].queryset.filter(plan__professional__user=request.user)
    if request.method=='POST' and frm.is_valid():
        try:
            result=save_appointment(frm.save(commit=False),request.user,frm.cleaned_data.get('occurrences',1));messages.success(request,f'{len(result)} consulta(s) salva(s).');return redirect('appointment_detail',pk=result[0].pk)
        except ValidationError as e:form_error(frm,e)
    return render(request,'core/form.html',{'title':'Editar consulta' if obj else 'Nova consulta','form':frm,'back':'/agenda/','hint':'Horários de São Paulo. Sessões recorrentes são semanais; todos os conflitos são validados antes de salvar.'})
@require('appointments')
def detail(request,pk):
    a=get_object_or_404(scope(request.user).select_related('patient','professional','procedure','room__branch'),pk=pk)
    return render(request,'appointments/detail.html',{'title':'Detalhes da consulta','a':a,'terminal':a.status in TERMINAL})
@require('appointments')
@require_POST
def status(request,pk):
    get_object_or_404(scope(request.user),pk=pk)
    try:transition(pk,request.POST.get('status'),request.user,request.POST.get('reason',''));messages.success(request,'Status atualizado.')
    except ValidationError as e:messages.error(request,' '.join(e.messages))
    return redirect('appointment_detail',pk=pk)
@require('appointments')
def events(request):
    qs=scope(request.user,Appointment.objects.select_related('patient','professional','procedure'))
    try:
        for field in ['start','end']:
            if request.GET.get(field):
                dt=parse_datetime(request.GET[field])
                if dt is None:raise ValueError
                qs=qs.filter(**{'end__gte' if field=='start' else 'start__lte':dt})
        qs=filter_appointments(qs,{k:int(request.GET[k]) for k in ['professional','procedure','branch'] if request.GET.get(k)})
        if request.GET.get('room'):qs=qs.filter(room_id=int(request.GET['room']))
        if request.GET.get('status'):qs=qs.filter(status=request.GET['status'])
    except (ValueError,TypeError):return JsonResponse({'error':'Filtro inválido.'},status=400)
    colors={'pending':'#cf932a','confirmed':'#078a82','in_progress':'#487ddd','completed':'#64748b','cancelled':'#d65a67','missed':'#aa4465','rescheduled':'#8662b6'}
    return JsonResponse([{'id':a.pk,'title':f'{a.patient.name} · {a.procedure.name}','start':a.start.isoformat(),'end':a.end.isoformat(),'backgroundColor':colors[a.status],'borderColor':colors[a.status],'url':f'/agenda/{a.pk}/','editable':a.status not in TERMINAL,'extendedProps':{'status':a.get_status_display(),'professional':a.professional.name}} for a in qs],safe=False)
@require('appointments')
@require_POST
def move(request,pk):
    get_object_or_404(scope(request.user),pk=pk)
    try:
        data=json.loads(request.body);start=parse_datetime(data['start']);end=parse_datetime(data['end'])
        if not start or not end or timezone.is_naive(start) or timezone.is_naive(end):raise ValueError
        reschedule(pk,start,end,request.user);return JsonResponse({'ok':True})
    except (ValueError,KeyError,TypeError):return JsonResponse({'error':'Horários inválidos.'},status=400)
    except ValidationError as e:return JsonResponse({'error':' '.join(e.messages)},status=409)
@require('appointments')
def slots(request):
    try:
        day=date.fromisoformat(request.GET.get('date',''));minutes=int(request.GET.get('duration',30))
        if not 5<=minutes<=480:raise ValueError
        pro=get_object_or_404(Professional,pk=int(request.GET.get('professional',0)),active=True);room=get_object_or_404(Room,pk=int(request.GET.get('room',0)),active=True)
    except (ValueError,TypeError):return JsonResponse({'error':'Selecione data, dentista, consultório e duração.'},status=400)
    if request.user.role=='dentist' and not request.user.is_manager and pro.user_id!=request.user.pk:return JsonResponse({'error':'Acesso negado.'},status=403)
    result=[]
    for window in pro.working_hours.filter(weekday=day.weekday()):
        current=timezone.make_aware(datetime.combine(day,window.start_time));stop=timezone.make_aware(datetime.combine(day,window.end_time))
        while current+timedelta(minutes=minutes)<=stop:
            end=current+timedelta(minutes=minutes)
            busy=Appointment.objects.exclude(status__in=['cancelled','missed']).filter(Q(professional=pro)|Q(room=room),start__lt=end,end__gt=current).exists()
            blocked=ScheduleBlock.objects.filter(professional=pro,start__lt=end,end__gt=current).exists()
            if not busy and not blocked:result.append({'start':current.isoformat(),'end':end.isoformat(),'label':current.strftime('%H:%M')})
            current+=timedelta(minutes=15)
    return JsonResponse({'slots':result})
