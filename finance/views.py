from decimal import Decimal,InvalidOperation
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.utils import timezone
from accounts.permissions import require
from core.views import selected_period,filter_context,resource_queryset
from core.catalog import RESOURCES
from core.forms import PaymentForm
from reports.services import finance_summary
from .models import Entry,Payment
from .services import pay,refund,cancel
@require('finance')
def dashboard(request):
    start,end,filters=selected_period(request)
    return render(request,'finance/dashboard.html',{'title':'Financeiro','start':start,'end':end,'stats':finance_summary(start,end,filters),**filter_context()})
@require('payments')
def detail(request,pk):
    e=get_object_or_404(resource_queryset(RESOURCES['lancamentos'],request.user),pk=pk)
    form=PaymentForm(request.POST or None,initial={'amount':e.balance,'paid_on':timezone.localdate(),'method':e.method})
    if request.method=='POST' and form.is_valid():
        try:pay(e,actor=request.user,**form.cleaned_data);messages.success(request,'Pagamento registrado.');return redirect('entry_detail',pk=pk)
        except ValidationError as error:
            for m in error.messages:form.add_error(None,m)
    return render(request,'finance/detail.html',{'title':e.description,'entry':e,'form':form,'payments':e.payments.select_related('actor'),'attachments':e.patient.attachments.filter(category='receipt') if e.patient_id else []})
@require('finance')
@require_POST
def refund_view(request,pk):
    p=get_object_or_404(Payment,pk=pk)
    try:refund(p,Decimal(request.POST.get('amount','0')),request.user,request.POST.get('reason',''));messages.success(request,'Estorno registrado.')
    except (InvalidOperation,ValueError):messages.error(request,'Valor inválido.')
    except ValidationError as e:messages.error(request,' '.join(e.messages))
    return redirect('entry_detail',pk=p.entry_id)
@require('finance')
@require_POST
def cancel_view(request,pk):
    e=get_object_or_404(Entry,pk=pk)
    try:cancel(e);messages.success(request,'Título cancelado.')
    except ValidationError as error:messages.error(request,' '.join(error.messages))
    return redirect('entry_detail',pk=pk)
