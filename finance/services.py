import calendar
from datetime import date
from decimal import Decimal
from uuid import uuid4
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.locks import lock_domain
from .models import Entry,Payment

def month_shift(day,months):
    n=day.month-1+months;y,m=day.year+n//12,n%12+1
    return date(y,m,min(day.day,calendar.monthrange(y,m)[1]))
@transaction.atomic
def create_entry(entry,installments=1):
    lock_domain('finance')
    if entry.pk:raise ValidationError('Lançamentos são preservados; cancele o título sem histórico e crie outro.')
    if not 1<=installments<=60:raise ValidationError('Use de 1 a 60 parcelas.')
    entry.full_clean();cents=int(entry.amount*100);discounts=int(entry.discount*100);group=uuid4() if installments>1 else None;rows=[]
    for i in range(installments):
        values={f.attname:getattr(entry,f.attname) for f in entry._meta.concrete_fields if f.name not in ['id','created_at','updated_at']}
        row=Entry(**values);row.amount=Decimal(cents//installments+(i<cents%installments))/100;row.discount=Decimal(discounts//installments+(i<discounts%installments))/100
        row.due_date=month_shift(entry.due_date,i);row.installment_group=group;row.installment_number=i+1
        if installments>1:row.description=f'{entry.description[:175]} ({i+1}/{installments})'
        row.save();rows.append(row)
    return rows
@transaction.atomic
def pay(entry,amount,paid_on,method,actor,note=''):
    lock_domain('finance');entry=Entry.objects.select_for_update().get(pk=entry.pk);amount=Decimal(str(amount))
    if not amount.is_finite() or amount<=0 or amount!=amount.quantize(Decimal('.01')):raise ValidationError('Valor positivo com até duas casas decimais obrigatório.')
    if entry.cancelled:raise ValidationError('Lançamento cancelado.')
    if amount>entry.balance:raise ValidationError('Pagamento maior que o saldo devedor.')
    if paid_on>timezone.localdate():raise ValidationError('Data de pagamento não pode ser futura.')
    return Payment.objects.create(entry=entry,amount=amount,paid_on=paid_on,method=method,actor=actor,note=note)
@transaction.atomic
def refund(payment,amount,actor,reason):
    lock_domain('finance');payment=Payment.objects.select_for_update().get(pk=payment.pk);amount=Decimal(str(amount))
    if payment.is_refund:raise ValidationError('Não é possível estornar um estorno.')
    available=payment.amount-sum((r.amount for r in payment.refunds.all()),Decimal('0'))
    if not amount.is_finite() or amount<=0 or amount>available:raise ValidationError('Valor de estorno inválido.')
    if not reason.strip():raise ValidationError('Informe o motivo do estorno.')
    return Payment.objects.create(entry=payment.entry,amount=amount,method=payment.method,actor=actor,note=reason,is_refund=True,original=payment,paid_on=timezone.localdate())
@transaction.atomic
def cancel(entry):
    lock_domain('finance');entry=Entry.objects.select_for_update().get(pk=entry.pk)
    if entry.payments.exists() or entry.appointment_id or entry.purchase_id:raise ValidationError('Título com histórico ou gerado por consulta/compra não pode ser cancelado manualmente.')
    entry.cancelled=True;entry.save()
