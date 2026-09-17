from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from core.models import Timestamped
class Appointment(Timestamped):
    STATUSES=[('pending','Pendente'),('confirmed','Confirmado'),('in_progress','Em atendimento'),('completed','Concluído'),('cancelled','Cancelado'),('missed','Não compareceu'),('rescheduled','Reagendado')]
    patient=models.ForeignKey('patients.Patient',on_delete=models.PROTECT,related_name='appointments',verbose_name='paciente')
    professional=models.ForeignKey('professionals.Professional',on_delete=models.PROTECT,verbose_name='dentista')
    procedure=models.ForeignKey('treatments.Procedure',on_delete=models.PROTECT,verbose_name='procedimento')
    room=models.ForeignKey('professionals.Room',on_delete=models.PROTECT,verbose_name='consultório')
    plan_item=models.ForeignKey('treatments.PlanItem',on_delete=models.PROTECT,null=True,blank=True,verbose_name='item do plano (opcional)')
    start=models.DateTimeField('início')
    end=models.DateTimeField('fim')
    value=models.DecimalField('valor da sessão',max_digits=12,decimal_places=2,validators=[MinValueValidator(0)])
    payment_method=models.CharField('forma de pagamento',max_length=20,default='pix',choices=[('pix','PIX'),('cash','Dinheiro'),('credit','Crédito'),('debit','Débito'),('boleto','Boleto'),('insurance','Convênio'),('transfer','Transferência')])
    status=models.CharField('status',max_length=20,choices=STATUSES,default='pending')
    notes=models.TextField('observações administrativas',blank=True)
    fit_in=models.BooleanField('encaixe fora do expediente',default=False)
    fit_in_reason=models.CharField('justificativa do encaixe',max_length=250,blank=True)
    cancellation_reason=models.CharField('motivo do cancelamento',max_length=250,blank=True)
    recurrence_id=models.UUIDField(null=True,blank=True,editable=False)
    completed_at=models.DateTimeField(null=True,blank=True,editable=False)
    material_cost=models.DecimalField(max_digits=12,decimal_places=2,default=0,editable=False)
    other_direct_cost=models.DecimalField(max_digits=12,decimal_places=2,default=0,editable=False)
    commission=models.DecimalField(max_digits=12,decimal_places=2,default=0,editable=False)
    def clean(self):
        if self.start and self.end and self.start>=self.end:raise ValidationError('Fim deve ser após o início.')
        if self.fit_in and not self.fit_in_reason:raise ValidationError('Justifique o encaixe.')
        if self.status=='cancelled' and not self.cancellation_reason:raise ValidationError('Informe o motivo do cancelamento.')
        if self.plan_item_id and (self.plan_item.plan.patient_id!=self.patient_id or self.plan_item.procedure_id!=self.procedure_id or self.plan_item.plan.professional_id!=self.professional_id):raise ValidationError('Item do plano incompatível com paciente/procedimento/dentista.')
    def __str__(self):return f'{self.patient} · {self.procedure}'
    class Meta:
        ordering=['start'];verbose_name='consulta'
        indexes=[models.Index(fields=['professional','start','end'])]
        constraints=[models.CheckConstraint(condition=models.Q(end__gt=models.F('start')),name='positive_duration')]
