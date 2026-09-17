from datetime import timedelta
from decimal import Decimal
from collections import Counter
from urllib.parse import quote
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError,PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from accounts.permissions import require,allowed
from .catalog import RESOURCES
from .forms import model_form,AccountCreateForm,EntryForm
from .models import Branch
from professionals.models import Professional
from treatments.models import Procedure
from patients.models import Patient
from inventory.models import Product
from appointments.models import Appointment
from appointments.services import scope
from reports.services import period,finance_summary,filter_appointments

def form_error(form,error):
    for message in error.messages:form.add_error(None,message)
def filter_context():return {'branches':Branch.objects.filter(active=True),'professionals':Professional.objects.filter(active=True),'procedures':Procedure.objects.filter(active=True)}
def selected_period(request):
    try:return period(request.GET)
    except ValidationError as e:messages.error(request,' '.join(e.messages));return period({})
@require('dashboard')
def dashboard(request):
    start,end,filters=selected_period(request);today=timezone.localdate()
    qs=scope(request.user,filter_appointments(Appointment.objects.select_related('patient','professional','procedure','room'),filters))
    todays=qs.filter(start__date=today).exclude(status='cancelled')
    period_qs=qs.filter(start__date__range=(start,end))
    data={'title':'Visão geral','today':today,'start':start,'end':end,**filter_context()}
    if allowed(request.user,'appointments'):
        data.update(today_count=todays.count(),upcoming=todays.order_by('start')[:8],active_patients=Patient.objects.filter(active=True).count(),confirmed=period_qs.filter(status='confirmed').count(),pending=period_qs.filter(status__in=['pending','rescheduled']).count(),completed=period_qs.filter(status='completed').count(),cancelled=period_qs.filter(status='cancelled').count(),top_procedures=Counter(a.procedure.name for a in period_qs.filter(status='completed')).most_common(5))
    if allowed(request.user,'finance'):
        data['stats']=finance_summary(start,end,filters)
        data['daily_income']=finance_summary(today,today,filters)['income'];data['annual_income']=finance_summary(today.replace(month=1,day=1),today,filters)['income']
        span=(end-start).days+1;data['previous']=finance_summary(start-timedelta(days=span),start-timedelta(days=1),filters)
    if allowed(request.user,'inventory'):
        products=list(Product.objects.filter(active=True).prefetch_related('batches'))
        data['low_products']=[p for p in products if p.quantity<=p.minimum][:6];data['stock_value']=sum((p.stock_value for p in products),Decimal('0'))
    return render(request,'core/dashboard.html',data)
def get_resource(key):
    if key not in RESOURCES:raise Http404
    return RESOURCES[key]
def resource_queryset(r,user):
    qs=r.model.objects.all()
    if r.kind=='entry':
        qs=qs.select_related('patient','supplier').prefetch_related('payments')
        if user.role=='reception' and not user.is_manager:qs=qs.filter(direction='in',patient__isnull=False)
    if r.kind=='product':qs=qs.prefetch_related('batches')
    if user.role=='dentist' and not user.is_manager:
        if r.model_name in ['professionals.ScheduleBlock','treatments.TreatmentPlan']:qs=qs.filter(professional__user=user)
        if r.model_name=='treatments.PlanItem':qs=qs.filter(plan__professional__user=user)
    return qs
def can_edit(user,r):return bool(r.edit_roles) and (user.is_manager or user.role in r.edit_roles)
def detail_url(r,obj):
    return {'patient':f'/pacientes/{obj.pk}/','purchase':f'/compras/{obj.pk}/','entry':f'/financeiro/lancamento/{obj.pk}/'}.get(r.kind)
@require('dashboard')
def resource_list(request,resource):
    r=get_resource(resource)
    if not allowed(request.user,r.area):raise PermissionDenied
    qs=resource_queryset(r,request.user);q=request.GET.get('q','').strip()
    if q:
        search=Q()
        for field in r.search:search|=Q(**{field+'__icontains':q})
        qs=qs.filter(search)
    fields={f.name for f in r.model._meta.fields}
    if 'active' in fields and request.GET.get('active') in ['true','false']:qs=qs.filter(active=request.GET['active']=='true')
    if 'status' in fields and request.GET.get('status'):qs=qs.filter(status=request.GET['status'])
    for field in ['professional','procedure','branch','plan','purchase']:
        if field in fields and request.GET.get(field,'').isdigit():qs=qs.filter(**{field+'_id':request.GET[field]})
    order=request.GET.get('order','');valid={field for _,field in r.columns if field in fields}
    if order.lstrip('-') in valid:qs=qs.order_by(order,'pk')
    elif not qs.ordered:qs=qs.order_by('pk')
    page=Paginator(qs,15).get_page(request.GET.get('page'));rows=[]
    for obj in page:
        cells=[]
        for _,field in r.columns:
            val=getattr(obj,field);cells.append(val() if callable(val) else val)
        editable=can_edit(request.user,r) and r.kind!='entry'
        if resource=='lotes' and obj.movement_set.exists():editable=False
        rows.append({'obj':obj,'cells':cells,'url':detail_url(r,obj),'can_edit':editable})
    return render(request,'core/list.html',{'title':r.title,'resource':resource,'r':r,'rows':rows,'page':page,'q':q,'can_create':can_edit(request.user,r),'has_active':'active' in fields,'statuses':r.model._meta.get_field('status').choices if 'status' in fields else [],'order_fields':[(label,field) for label,field in r.columns if field in valid]})
@require('dashboard')
def resource_form(request,resource,pk=None):
    r=get_resource(resource)
    if not allowed(request.user,r.area) or not can_edit(request.user,r):raise PermissionDenied
    obj=get_object_or_404(resource_queryset(r,request.user),pk=pk) if pk else None
    if r.kind=='entry' and obj:raise PermissionDenied
    if resource=='lotes' and obj and obj.movement_set.exists():raise PermissionDenied
    klass=EntryForm if r.kind=='entry' else AccountCreateForm if r.kind=='user' and not obj else model_form(r.model,r.fields)
    initial={field:request.GET[field] for field in klass.base_fields if request.GET.get(field,'').isdigit()}
    form=klass(request.POST or None,instance=obj,initial=initial)
    if request.user.role=='dentist' and not request.user.is_manager:
        if 'professional' in form.fields:form.fields['professional'].queryset=Professional.objects.filter(user=request.user)
        if 'plan' in form.fields:form.fields['plan'].queryset=form.fields['plan'].queryset.filter(professional__user=request.user)
    if resource=='profissionais':form.fields['user'].queryset=form.fields['user'].queryset.filter(role__in=['dentist','admin'])
    if resource=='compras':form.fields['status'].choices=[x for x in form.fields['status'].choices if x[0]!='received']
    if r.kind=='entry' and request.user.role=='reception' and not request.user.is_manager:
        form.fields['direction'].choices=[('in','Receita')];form.fields['category'].choices=[('service','Atendimento'),('other','Outros')];form.fields['patient'].required=True;form.fields.pop('supplier')
    if request.method=='POST' and form.is_valid():
        try:
            with transaction.atomic():
                instance=form.save(commit=False)
                if resource=='pacientes' and instance.privacy_acknowledged and not instance.privacy_at:instance.privacy_at=timezone.now()
                if resource in ['horarios','bloqueios']:
                    from appointments.services import save_calendar_setting
                    save_calendar_setting(instance)
                elif r.kind=='entry':
                    from finance.services import create_entry
                    instance=create_entry(instance,form.cleaned_data['installments'])[0]
                elif resource in ['compras','itens-compra']:
                    from purchases.services import save_order
                    save_order(instance,request.user)
                elif resource=='lotes':
                    from core.locks import lock_domain
                    lock_domain('inventory')
                    if instance.pk and instance.movement_set.exists():raise ValidationError('Lote com movimentações não pode ser editado.')
                    instance.save()
                else:instance.save()
                if hasattr(form,'save_m2m'):form.save_m2m()
            messages.success(request,'Registro salvo com sucesso.')
            return redirect(detail_url(r,instance) or f'/cadastros/{resource}/')
        except ValidationError as e:form_error(form,e)
    return render(request,'core/form.html',{'title':('Editar · ' if obj else 'Novo registro · ')+r.title,'form':form,'back':f'/cadastros/{resource}/','hint':'As parcelas dividem o valor total e vencem mês a mês.' if r.kind=='entry' else ''})
@require('settings')
def settings_page(request):return render(request,'core/settings.html',{'title':'Configurações'})
@require('dashboard')
def search(request):
    query=request.GET.get('q','').strip();groups=[]
    if query:
        for key in ['pacientes','profissionais','procedimentos','materiais','fornecedores','lancamentos']:
            r=RESOURCES[key]
            if not allowed(request.user,r.area):continue
            q=Q()
            for field in r.search:q|=Q(**{field+'__icontains':query})
            groups.append({'title':r.title,'items':[{'label':str(x),'url':detail_url(r,x) or f'/cadastros/{key}/?q={quote(query)}'} for x in resource_queryset(r,request.user).filter(q)[:8]]})
    return render(request,'core/search.html',{'title':'Busca global','q':query,'groups':groups})
@require('dashboard')
def privacy(request):return render(request,'core/privacy.html',{'title':'Privacidade'})
