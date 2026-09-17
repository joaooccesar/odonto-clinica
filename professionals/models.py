from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator,MaxValueValidator
from django.core.exceptions import ValidationError
from core.models import Timestamped,ValidatedModel
class Professional(Timestamped):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True,related_name='professional',verbose_name='usuário dentista')
    name=models.CharField('nome',max_length=140)
    specialty=models.CharField('especialidade',max_length=120)
    cro=models.CharField('CRO / UF',max_length=30,unique=True)
    phone=models.CharField('telefone',max_length=25,blank=True)
    email=models.EmailField('e-mail',blank=True)
    commission_percent=models.DecimalField('comissão (%)',max_digits=5,decimal_places=2,default=0,validators=[MinValueValidator(0),MaxValueValidator(100)])
    commission_fixed=models.DecimalField('comissão fixa (substitui percentual)',max_digits=12,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    active=models.BooleanField('ativo',default=True)
    def clean(self):
        if self.user_id and self.user.role not in ['dentist','admin']:raise ValidationError('Vincule um usuário dentista ou administrador.')
    def __str__(self):return self.name
    class Meta: ordering=['name'];verbose_name='profissional';verbose_name_plural='profissionais'
class Room(Timestamped):
    name=models.CharField('nome',max_length=90)
    branch=models.ForeignKey('core.Branch',on_delete=models.PROTECT,verbose_name='unidade')
    active=models.BooleanField('ativo',default=True)
    def __str__(self):return f'{self.name} · {self.branch}'
    class Meta:
        verbose_name='consultório'
        constraints=[models.UniqueConstraint(fields=['name','branch'],name='room_branch_unique')]
class Availability(ValidatedModel):
    professional=models.ForeignKey(Professional,on_delete=models.PROTECT,related_name='working_hours',verbose_name='dentista')
    weekday=models.PositiveSmallIntegerField('dia da semana',choices=list(enumerate(['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo'])))
    start_time=models.TimeField('início')
    end_time=models.TimeField('fim')
    def clean(self):
        if self.start_time and self.end_time and self.start_time>=self.end_time:raise ValidationError('O fim deve ocorrer após o início.')
    def __str__(self):return f'{self.professional} · {self.get_weekday_display()} {self.start_time}–{self.end_time}'
    class Meta:verbose_name='horário de atendimento';verbose_name_plural='horários de atendimento'
class ScheduleBlock(Timestamped):
    professional=models.ForeignKey(Professional,on_delete=models.PROTECT,verbose_name='dentista')
    start=models.DateTimeField('início')
    end=models.DateTimeField('fim')
    reason=models.CharField('motivo',max_length=250)
    def clean(self):
        if self.start and self.end:
            if self.start>=self.end:raise ValidationError('O fim deve ocorrer após o início.')
            from appointments.models import Appointment
            if self.professional_id and Appointment.objects.filter(professional_id=self.professional_id,start__lt=self.end,end__gt=self.start).exclude(status__in=['cancelled','missed']).exists():raise ValidationError('Reagende ou cancele as consultas antes de bloquear o intervalo.')
    def __str__(self):return f'{self.professional} · {self.reason}'
    class Meta:verbose_name='bloqueio de agenda'
