from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.locks import lock_domain
from inventory.models import Batch
from inventory.services import move
from finance.models import Entry
from .models import Purchase
@transaction.atomic
def receive(purchase,actor):
    lock_domain('purchases');purchase=Purchase.objects.select_for_update().get(pk=purchase.pk)
    if purchase.status=='received':return purchase
    if purchase.status=='cancelled':raise ValidationError('Pedido cancelado.')
    items=list(purchase.items.select_related('product').order_by('pk'))
    if not items:raise ValidationError('Adicione pelo menos um item.')
    lock_domain('inventory')
    for item in items:
        if item.expiry and item.expiry<timezone.localdate():raise ValidationError('Não é possível receber lote vencido.')
        batch,new=Batch.objects.get_or_create(product=item.product,number=item.batch_number,defaults={'expiry':item.expiry,'unit_cost':item.unit_cost})
        if not new and (batch.expiry!=item.expiry or batch.unit_cost!=item.unit_cost):raise ValidationError('Lote existente com custo ou validade diferentes. Use identificador de lote distinto.')
        move(batch,item.quantity,'purchase',f'Pedido #{purchase.pk}',actor,purchase=purchase)
    lock_domain('finance')
    if purchase.total>0:Entry.objects.create(direction='out',category='purchase',description=f'Compra #{purchase.pk}',branch=purchase.branch,supplier=purchase.supplier,amount=purchase.total.quantize(Decimal('.01')),due_date=purchase.due_date,purchase=purchase)
    purchase.status='received';purchase.received_at=timezone.now();purchase.responsible=actor;purchase.save();return purchase
@transaction.atomic
def save_order(obj,actor):
    lock_domain('purchases')
    if isinstance(obj,Purchase):
        if obj.pk and Purchase.objects.get(pk=obj.pk).status in ['received','cancelled']:raise ValidationError('Pedido encerrado não permite edição.')
        if obj.status=='received':raise ValidationError('Use a ação Confirmar recebimento.')
        obj.responsible=actor
    obj.save();return obj
