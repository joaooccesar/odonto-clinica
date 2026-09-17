from datetime import timedelta
from decimal import Decimal
from uuid import uuid4
from django.db import transaction
from django.db.models import Q
from django.core.exceptions import ValidationError,PermissionDenied
from django.utils import timezone
from core.locks import lock_domain
from professionals.models import ScheduleBlock
from .models import Appointment
TERMINAL={'completed','cancelled','missed'}
def scope(user,queryset=None):
    qs=queryset if queryset is not None else Appointment.objects.all()
    return qs.filter(professional__user=user) if user.role=='dentist' and not user.is_manager else qs

def validate_schedule(a):
    a.full_clean()
    if not(a.patient.active and a.professional.active and a.procedure.active and a.room.active and a.room.branch.active):raise ValidationError('Paciente, dentista, procedimento e consultório devem estar ativos.')
    if timezone.is_naive(a.start) or timezone.is_naive(a.end):raise ValidationError('Horários precisam incluir o fuso horário.')
    start,end=timezone.localtime(a.start),timezone.localtime(a.end)
    if start.date()!=end.date() or a.end-a.start>timedelta(hours=8):raise ValidationError('Consulta deve ocorrer no mesmo dia e durar no máximo oito horas.')
    if a.procedure.professionals.exists() and not a.procedure.professionals.filter(pk=a.professional_id).exists():raise ValidationError('Profissional não habilitado para este procedimento.')
    if a.plan_item_id:
        if a.plan_item.completed_sessions>=a.plan_item.sessions:raise ValidationError('Todas as sessões deste item já foram concluídas.')
        if a.plan_item.plan.status not in ['accepted','ongoing']:raise ValidationError('Registre o aceite do plano antes de agendar suas sessões.')
    busy=Appointment.objects.exclude(pk=a.pk).exclude(status__in=['cancelled','missed']).filter(start__lt=a.end,end__gt=a.start)
    if busy.filter(Q(professional_id=a.professional_id)|Q(room_id=a.room_id)|Q(patient_id=a.patient_id)).exists():raise ValidationError('Conflito de horário para o dentista, consultório ou paciente.')
    if ScheduleBlock.objects.filter(professional=a.professional,start__lt=a.end,end__gt=a.start).exists():raise ValidationError('Dentista com bloqueio nesse intervalo.')
    if not a.fit_in and not a.professional.working_hours.filter(weekday=start.weekday(),start_time__lte=start.time(),end_time__gte=end.time()).exists():raise ValidationError('Fora do expediente. Cadastre um horário ou justifique o encaixe.')

@transaction.atomic
def save_appointment(a,actor,occurrences=1):
    lock_domain('appointments')
    if actor.role=='dentist' and not actor.is_manager and a.professional.user_id!=actor.pk:raise PermissionDenied
    if a.pk:
        old=Appointment.objects.get(pk=a.pk)
        if old.status in TERMINAL:raise ValidationError('Consulta encerrada não pode ser alterada.')
        if old.status!=a.status:raise ValidationError('Use a ação própria para mudar o status.')
        if occurrences!=1:raise ValidationError('Recorrência só pode ser criada em nova consulta.')
    elif a.status!='pending':raise ValidationError('Nova consulta deve começar pendente.')
    if not 1<=occurrences<=26:raise ValidationError('Informe de 1 a 26 sessões semanais.')
    validate_schedule(a)
    if occurrences>1:a.recurrence_id=uuid4()
    a.save();result=[a]
    for week in range(1,occurrences):
        values={f.attname:getattr(a,f.attname) for f in a._meta.concrete_fields if f.name not in ['id','created_at','updated_at']}
        row=Appointment(**values);row.start=a.start+timedelta(weeks=week);row.end=a.end+timedelta(weeks=week)
        validate_schedule(row);row.save();result.append(row)
    return result
@transaction.atomic
def reschedule(pk,start,end,actor):
    lock_domain('appointments');a=scope(actor).get(pk=pk)
    if a.status in TERMINAL:raise ValidationError('Consulta encerrada não pode ser reagendada.')
    a.start,a.end=start,end;validate_schedule(a);a.status='rescheduled';a.save();return a
@transaction.atomic
def transition(pk,status,actor,reason=''):
    lock_domain('appointments');a=scope(actor).select_for_update().get(pk=pk)
    if a.status==status=='completed':return a
    permitted={'pending':{'confirmed','in_progress','cancelled','missed'},'confirmed':{'in_progress','completed','cancelled','missed'},'in_progress':{'completed','cancelled'},'rescheduled':{'confirmed','in_progress','completed','cancelled','missed'}}
    if status not in permitted.get(a.status,set()):raise ValidationError('Transição de status não permitida.')
    if status in ['completed','missed'] and a.start>timezone.now():raise ValidationError('Não é possível concluir ou registrar falta antes do horário da consulta.')
    if status=='cancelled':
        if not reason.strip():raise ValidationError('Informe o motivo do cancelamento.')
        a.cancellation_reason=reason
    if status=='completed':
        from inventory.services import consume
        from finance.models import Entry
        a.material_cost=consume(a,actor);a.other_direct_cost=a.procedure.estimated_cost
        a.commission=(a.professional.commission_fixed or a.value*a.professional.commission_percent/100).quantize(Decimal('.01'))
        a.completed_at=timezone.now();lock_domain('finance')
        shared=dict(branch=a.room.branch,patient=a.patient,professional=a.professional,procedure=a.procedure,appointment=a,due_date=timezone.localdate(),method=a.payment_method)
        if a.value>0:Entry.objects.create(direction='in',category='service',description=f'Consulta #{a.pk} · {a.procedure.name}',amount=a.value,**shared)
        if a.commission>0:Entry.objects.create(direction='out',category='commission',description=f'Comissão da consulta #{a.pk}',amount=a.commission,**shared)
        if a.plan_item_id:
            item=a.plan_item
            if item.completed_sessions>=item.sessions:raise ValidationError('O plano já concluiu todas as sessões.')
            item.completed_sessions+=1;item.save()
    a.status=status;a.save();return a
@transaction.atomic
def save_calendar_setting(obj):
    lock_domain('appointments');obj.save();return obj
