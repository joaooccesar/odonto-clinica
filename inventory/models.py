from decimal import Decimal
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from core.models import Timestamped,Immutable
class Product(Timestamped):
    name=models.CharField('nome',max_length=150)
    category=models.CharField('categoria',max_length=100)
    code=models.CharField('código interno',max_length=50,unique=True)
    barcode=models.CharField('código de barras',max_length=70,blank=True)
    unit=models.CharField('unidade de medida',max_length=15,default='un')
    minimum=models.DecimalField('estoque mínimo',max_digits=12,decimal_places=3,default=0,validators=[MinValueValidator(0)])
    maximum=models.DecimalField('estoque máximo (zero: não definido)',max_digits=12,decimal_places=3,default=0,validators=[MinValueValidator(0)])
    manufacturer=models.CharField('fabricante',max_length=100,blank=True)
    supplier=models.ForeignKey('suppliers.Supplier',on_delete=models.PROTECT,null=True,blank=True,verbose_name='fornecedor')
    location=models.CharField('local de armazenamento',max_length=100,blank=True)
    active=models.BooleanField('ativo',default=True)
    @property
    def quantity(self):return sum((b.quantity for b in self.batches.all()),Decimal('0'))
    @property
    def stock_value(self):return sum((b.quantity*b.unit_cost for b in self.batches.all()),Decimal('0'))
    @property
    def suggestion(self):return max(Decimal('0'),self.minimum-self.quantity)
    def clean(self):
        if self.maximum and self.maximum<self.minimum:raise ValidationError('Máximo não pode ser menor que mínimo.')
    def __str__(self):return f'{self.name} ({self.unit})'
    class Meta:ordering=['name'];verbose_name='material';verbose_name_plural='materiais'
class Batch(Timestamped):
    product=models.ForeignKey(Product,on_delete=models.PROTECT,related_name='batches',verbose_name='material')
    number=models.CharField('lote',max_length=70)
    expiry=models.DateField('validade',null=True,blank=True)
    quantity=models.DecimalField('saldo',max_digits=12,decimal_places=3,default=0,editable=False)
    unit_cost=models.DecimalField('custo unitário',max_digits=12,decimal_places=4,default=0,validators=[MinValueValidator(0)])
    def __str__(self):return f'{self.product.name} · lote {self.number} · saldo {self.quantity}'
    class Meta:
        verbose_name='lote'
        constraints=[models.UniqueConstraint(fields=['product','number'],name='product_batch_unique'),models.CheckConstraint(condition=models.Q(quantity__gte=0),name='nonnegative_stock')]
class Movement(Immutable):
    KINDS=[('entry','Entrada'),('purchase','Compra'),('manual','Saída manual'),('procedure','Consumo em procedimento'),('adjustment','Ajuste'),('loss','Perda'),('expired','Vencimento'),('return','Devolução')]
    batch=models.ForeignKey(Batch,on_delete=models.PROTECT,verbose_name='lote')
    kind=models.CharField('tipo',max_length=20,choices=KINDS)
    delta=models.DecimalField('variação',max_digits=12,decimal_places=3)
    unit_cost=models.DecimalField('custo registrado',max_digits=12,decimal_places=4)
    balance_after=models.DecimalField('saldo após',max_digits=12,decimal_places=3)
    reason=models.CharField('motivo',max_length=250)
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,verbose_name='responsável')
    appointment=models.ForeignKey('appointments.Appointment',on_delete=models.PROTECT,null=True,blank=True)
    purchase=models.ForeignKey('purchases.Purchase',on_delete=models.PROTECT,null=True,blank=True)
    created_at=models.DateTimeField('data',auto_now_add=True)
    class Meta:ordering=['-created_at'];verbose_name='movimentação';verbose_name_plural='movimentações'
