from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator,MaxValueValidator
from django.core.exceptions import ValidationError
from core.models import Timestamped,ValidatedModel
class Procedure(Timestamped):
    name=models.CharField('nome',max_length=150)
    category=models.CharField('categoria',max_length=100)
    description=models.TextField('descrição',blank=True)
    duration=models.PositiveIntegerField('duração (minutos)',default=30,validators=[MinValueValidator(5),MaxValueValidator(480)])
    price=models.DecimalField('preço por sessão',max_digits=12,decimal_places=2,validators=[MinValueValidator(0)])
    estimated_cost=models.DecimalField('outros custos diretos por sessão (sem materiais/comissões)',max_digits=12,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    specialty=models.CharField('especialidade',max_length=100,blank=True)
    sessions=models.PositiveIntegerField('sessões',default=1,validators=[MinValueValidator(1)])
    professionals=models.ManyToManyField('professionals.Professional',blank=True,verbose_name='dentistas habilitados (vazio: todos)')
    active=models.BooleanField('ativo',default=True)
    def __str__(self):return self.name
    class Meta:ordering=['name'];verbose_name='procedimento'
class ProcedureMaterial(ValidatedModel):
    procedure=models.ForeignKey(Procedure,on_delete=models.PROTECT,related_name='materials',verbose_name='procedimento')
    product=models.ForeignKey('inventory.Product',on_delete=models.PROTECT,verbose_name='material')
    quantity=models.DecimalField('quantidade por sessão',max_digits=12,decimal_places=3,validators=[MinValueValidator(Decimal('.001'))])
    def __str__(self):return f'{self.procedure} · {self.product} × {self.quantity}'
    class Meta:
        verbose_name='material do procedimento'
        constraints=[models.UniqueConstraint(fields=['procedure','product'],name='procedure_material_unique')]
class TreatmentPlan(Timestamped):
    patient=models.ForeignKey('patients.Patient',on_delete=models.PROTECT,related_name='plans',verbose_name='paciente')
    professional=models.ForeignKey('professionals.Professional',on_delete=models.PROTECT,verbose_name='dentista')
    name=models.CharField('título',max_length=150)
    status=models.CharField('status',max_length=20,default='proposed',choices=[('proposed','Proposto'),('accepted','Aceito'),('ongoing','Em andamento'),('completed','Concluído'),('cancelled','Cancelado')])
    discount=models.DecimalField('desconto total',max_digits=12,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    payment_method=models.CharField('forma de pagamento',max_length=80,blank=True)
    installments=models.PositiveIntegerField('parcelas',default=1,validators=[MinValueValidator(1),MaxValueValidator(60)])
    acceptance=models.TextField('registro do aceite',blank=True)
    accepted_at=models.DateTimeField('aceito em',null=True,blank=True)
    @property
    def total(self):return max(Decimal('0'),sum((i.price*i.sessions for i in self.items.all()),Decimal('0'))-self.discount)
    def clean(self):
        if self.status in ['accepted','ongoing','completed'] and not(self.acceptance and self.accepted_at):raise ValidationError('Registre o aceite e a data.')
    def __str__(self):return f'{self.patient} · {self.name}'
    class Meta:verbose_name='plano de tratamento'
class PlanItem(Timestamped):
    plan=models.ForeignKey(TreatmentPlan,on_delete=models.PROTECT,related_name='items',verbose_name='plano')
    procedure=models.ForeignKey(Procedure,on_delete=models.PROTECT,verbose_name='procedimento')
    teeth=models.CharField('dentes envolvidos',max_length=100,blank=True)
    sessions=models.PositiveIntegerField('sessões previstas',default=1,validators=[MinValueValidator(1)])
    completed_sessions=models.PositiveIntegerField('sessões concluídas',default=0,editable=False)
    price=models.DecimalField('preço por sessão',max_digits=12,decimal_places=2,validators=[MinValueValidator(0)])
    def clean(self):
        if self.completed_sessions and self.sessions<self.completed_sessions:raise ValidationError('As sessões previstas não podem ser menores que as concluídas.')
    def __str__(self):return f'{self.plan} · {self.procedure} ({self.completed_sessions}/{self.sessions})'
    class Meta:verbose_name='item do tratamento'
