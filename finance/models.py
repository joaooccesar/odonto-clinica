from decimal import Decimal
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.models import Timestamped,Immutable
METHODS=[('pix','PIX'),('cash','Dinheiro'),('credit','Crédito'),('debit','Débito'),('boleto','Boleto'),('insurance','Convênio'),('transfer','Transferência')]
class Entry(Timestamped):
    direction=models.CharField('tipo',max_length=3,choices=[('in','Receita'),('out','Despesa')])
    category=models.CharField('categoria',max_length=20,default='service',choices=[('service','Atendimento'),('fixed','Despesa fixa'),('variable','Despesa variável'),('direct','Custo direto'),('tax','Imposto'),('commission','Comissão'),('purchase','Compra de estoque'),('other','Outros')])
    description=models.CharField('descrição',max_length=200)
    branch=models.ForeignKey('core.Branch',on_delete=models.PROTECT,verbose_name='unidade')
    patient=models.ForeignKey('patients.Patient',on_delete=models.PROTECT,null=True,blank=True,related_name='entries',verbose_name='paciente')
    supplier=models.ForeignKey('suppliers.Supplier',on_delete=models.PROTECT,null=True,blank=True,verbose_name='fornecedor')
    professional=models.ForeignKey('professionals.Professional',on_delete=models.PROTECT,null=True,blank=True,verbose_name='dentista')
    procedure=models.ForeignKey('treatments.Procedure',on_delete=models.PROTECT,null=True,blank=True,verbose_name='procedimento')
    appointment=models.ForeignKey('appointments.Appointment',on_delete=models.PROTECT,null=True,blank=True)
    purchase=models.OneToOneField('purchases.Purchase',on_delete=models.PROTECT,null=True,blank=True)
    cost_center=models.CharField('centro de custo',max_length=100,blank=True)
    amount=models.DecimalField('valor bruto',max_digits=12,decimal_places=2,validators=[MinValueValidator(Decimal('.01'))])
    discount=models.DecimalField('desconto',max_digits=12,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    issue_date=models.DateField('emissão',default=timezone.localdate)
    due_date=models.DateField('vencimento')
    method=models.CharField('método previsto',max_length=20,choices=METHODS,default='pix')
    installment_group=models.UUIDField(null=True,blank=True,editable=False)
    installment_number=models.PositiveIntegerField(default=1,editable=False)
    cancelled=models.BooleanField(default=False,editable=False)
    @property
    def net(self):return self.amount-self.discount
    @property
    def paid(self):return sum(((-p.amount if p.is_refund else p.amount) for p in self.payments.all()),Decimal('0'))
    @property
    def balance(self):return self.net-self.paid
    @property
    def status(self):
        if self.cancelled:return 'Cancelado'
        if self.balance<=0:return 'Quitado'
        if self.due_date<timezone.localdate():return 'Em atraso'
        return 'Parcial' if self.paid else 'Em aberto'
    def clean(self):
        if self.discount is not None and self.amount is not None and self.discount>=self.amount:raise ValidationError('Desconto deve ser menor que o valor bruto.')
        if self.category=='service' and self.direction!='in':raise ValidationError('Atendimentos são receitas.')
        if self.category in ['fixed','variable','direct','tax','commission','purchase'] and self.direction!='out':raise ValidationError('Categoria exclusiva de despesas.')
    def __str__(self):return self.description
    class Meta:ordering=['due_date','pk'];verbose_name='lançamento';verbose_name_plural='lançamentos'
class Payment(Immutable):
    entry=models.ForeignKey(Entry,on_delete=models.PROTECT,related_name='payments',verbose_name='lançamento')
    amount=models.DecimalField('valor',max_digits=12,decimal_places=2,validators=[MinValueValidator(Decimal('.01'))])
    paid_on=models.DateField('data',default=timezone.localdate)
    method=models.CharField('forma de pagamento',max_length=20,choices=METHODS)
    is_refund=models.BooleanField(default=False)
    original=models.ForeignKey('self',on_delete=models.PROTECT,null=True,blank=True,related_name='refunds')
    note=models.CharField('observação / motivo',max_length=250,blank=True)
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:ordering=['-created_at'];verbose_name='pagamento'
