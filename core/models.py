from django.db import models
from django.core.exceptions import ValidationError
class ValidatedModel(models.Model):
    class Meta: abstract = True
    def save(self,*args,**kwargs):
        self.full_clean()
        return super().save(*args,**kwargs)
class Timestamped(ValidatedModel):
    created_at=models.DateTimeField('criado em',auto_now_add=True)
    updated_at=models.DateTimeField('atualizado em',auto_now=True)
    class Meta: abstract=True
class Immutable(ValidatedModel):
    class Meta: abstract=True
    def save(self,*args,**kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError('Registro preservado. Crie uma retificação ou estorno.')
        return super().save(*args,**kwargs)
    def delete(self,*args,**kwargs): raise ValidationError('Registro não pode ser excluído.')
class Branch(Timestamped):
    name=models.CharField('nome',max_length=100)
    address=models.CharField('endereço',max_length=250,blank=True)
    active=models.BooleanField('ativa',default=True)
    def __str__(self):return self.name
    class Meta: verbose_name='unidade'
class BusinessLock(models.Model):
    key=models.CharField(max_length=60,unique=True)
class LoginAttempt(models.Model):
    key=models.CharField(max_length=64,unique=True)
    count=models.PositiveIntegerField(default=0)
    since=models.DateTimeField()
