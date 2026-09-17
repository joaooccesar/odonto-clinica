from django.conf import settings
from django.db import models
from core.models import Immutable
class AuditLog(Immutable):
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True)
    action=models.CharField(max_length=80)
    model=models.CharField(max_length=100)
    object_id=models.CharField(max_length=80,blank=True)
    detail=models.CharField(max_length=300,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:ordering=['-created_at'];verbose_name='evento de auditoria'
