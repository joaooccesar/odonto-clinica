from django.conf import settings
from django.db import models
from core.models import Timestamped
class Reminder(Timestamped):
    appointment=models.ForeignKey('appointments.Appointment',on_delete=models.PROTECT)
    channel=models.CharField(max_length=15,choices=[('email','E-mail'),('whatsapp','WhatsApp')])
    status=models.CharField(max_length=15,default='draft',choices=[('draft','Preparado'),('sent','Enviado'),('error','Erro')])
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    sent_at=models.DateTimeField(null=True,blank=True)
    error=models.CharField(max_length=200,blank=True)
    class Meta:verbose_name='lembrete'
