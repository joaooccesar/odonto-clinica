from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from core.models import Timestamped
class Purchase(Timestamped):
    supplier=models.ForeignKey('suppliers.Supplier',on_delete=models.PROTECT,verbose_name='fornecedor')
    branch=models.ForeignKey('core.Branch',on_delete=models.PROTECT,verbose_name='unidade')
    order_date=models.DateField('data do pedido')
    expected_date=models.DateField('previsão de entrega')
    due_date=models.DateField('vencimento')
    invoice_number=models.CharField('nota fiscal',max_length=80,blank=True)
    payment_method=models.CharField('forma de pagamento',max_length=70,blank=True)
    status=models.CharField('status',max_length=20,default='draft',choices=[('draft','Aberto'),('ordered','Enviado'),('received','Recebido'),('cancelled','Cancelado')])
    received_at=models.DateTimeField(null=True,blank=True,editable=False)
    responsible=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,editable=False)
    @property
    def total(self):return sum((i.quantity*i.unit_cost for i in self.items.all()),Decimal('0'))
    def __str__(self):return f'Pedido #{self.pk} · {self.supplier}'
    class Meta:verbose_name='pedido de compra'
class PurchaseItem(Timestamped):
    purchase=models.ForeignKey(Purchase,on_delete=models.PROTECT,related_name='items',verbose_name='pedido')
    product=models.ForeignKey('inventory.Product',on_delete=models.PROTECT,verbose_name='material')
    quantity=models.DecimalField('quantidade',max_digits=12,decimal_places=3,validators=[MinValueValidator(Decimal('.001'))])
    unit_cost=models.DecimalField('custo unitário',max_digits=12,decimal_places=4,validators=[MinValueValidator(0)])
    batch_number=models.CharField('lote',max_length=70)
    expiry=models.DateField('validade',null=True,blank=True)
    def clean(self):
        if self.purchase_id and self.purchase.status not in ['draft','ordered']:raise ValidationError('Pedido encerrado não permite alterações.')
    def __str__(self):return f'{self.product} × {self.quantity}'
    class Meta:verbose_name='item de compra'
