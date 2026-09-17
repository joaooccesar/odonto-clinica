from decimal import Decimal
from django.db import transaction
from django.db.models import F,Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.locks import lock_domain
from .models import Batch,Movement
@transaction.atomic
def move(batch,delta,kind,reason,actor,appointment=None,purchase=None):
    lock_domain('inventory')
    batch=Batch.objects.select_for_update().get(pk=batch.pk)
    delta=Decimal(str(delta))
    if not delta.is_finite() or delta==0 or delta!=delta.quantize(Decimal('.001')):raise ValidationError('Informe quantidade diferente de zero, com até três casas decimais.')
    if not reason.strip():raise ValidationError('Informe o motivo.')
    if batch.quantity+delta<0:raise ValidationError(f'Estoque insuficiente no lote {batch.number}: saldo {batch.quantity}.')
    if kind in ['manual','procedure','loss','expired'] and delta>0:raise ValidationError('Esse tipo exige uma saída (quantidade negativa).')
    if kind in ['entry','purchase'] and delta<0:raise ValidationError('Entrada deve ser positiva.')
    batch.quantity+=delta;batch.save(update_fields=['quantity','updated_at'])
    return Movement.objects.create(batch=batch,kind=kind,delta=delta,reason=reason,actor=actor,unit_cost=batch.unit_cost,balance_after=batch.quantity,appointment=appointment,purchase=purchase)
@transaction.atomic
def consume(appointment,actor):
    lock_domain('inventory');total=Decimal('0')
    for recipe in appointment.procedure.materials.select_related('product').order_by('product_id'):
        remaining=recipe.quantity
        batches=Batch.objects.filter(product=recipe.product,quantity__gt=0).filter(Q(expiry__isnull=True)|Q(expiry__gte=timezone.localdate())).order_by(F('expiry').asc(nulls_last=True),'pk')
        for batch in batches:
            qty=min(remaining,batch.quantity)
            if qty>0:
                move(batch,-qty,'procedure',f'Consulta #{appointment.pk}',actor,appointment=appointment)
                total+=qty*batch.unit_cost;remaining-=qty
            if remaining<=0:break
        if remaining>0:raise ValidationError(f'Material insuficiente em lotes válidos: {recipe.product.name}. Faltam {remaining} {recipe.product.unit}.')
    return total.quantize(Decimal('.01'))
