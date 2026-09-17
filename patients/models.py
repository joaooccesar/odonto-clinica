import re
from datetime import date
from django.db import models
from django.core.exceptions import ValidationError
from core.models import Timestamped
def validate_cpf(value):
    d=re.sub(r'\D','',value or '')
    if not d:return
    if len(d)!=11 or len(set(d))==1:raise ValidationError('CPF inválido.')
    for n in (9,10):
        check=(sum(int(d[i])*(n+1-i) for i in range(n))*10%11)%10
        if check!=int(d[n]):raise ValidationError('CPF inválido.')
class Patient(Timestamped):
    name=models.CharField('nome completo',max_length=160)
    cpf=models.CharField('CPF',max_length=14,null=True,blank=True,unique=True,validators=[validate_cpf])
    birth_date=models.DateField('nascimento',null=True,blank=True)
    phone=models.CharField('telefone / WhatsApp',max_length=25,blank=True)
    email=models.EmailField('e-mail',blank=True)
    address=models.TextField('endereço',blank=True)
    gender=models.CharField('gênero',max_length=60,blank=True)
    occupation=models.CharField('profissão',max_length=100,blank=True)
    insurance=models.CharField('convênio',max_length=100,blank=True)
    insurance_number=models.CharField('carteirinha',max_length=80,blank=True)
    emergency_contact=models.CharField('contato de emergência',max_length=180,blank=True)
    notes=models.TextField('observações administrativas',blank=True)
    active=models.BooleanField('ativo',default=True)
    privacy_acknowledged=models.BooleanField('ciência da política de privacidade registrada',default=False)
    privacy_at=models.DateTimeField(null=True,blank=True,editable=False)
    reminder_consent=models.BooleanField('autoriza lembretes',default=False)
    anonymized_at=models.DateTimeField(null=True,blank=True,editable=False)
    def clean(self):
        self.cpf=re.sub(r'\D','',self.cpf or '') or None
        if self.birth_date and self.birth_date>date.today():raise ValidationError({'birth_date':'Data futura inválida.'})
    def __str__(self):return self.name
    class Meta: ordering=['name'];verbose_name='paciente'
