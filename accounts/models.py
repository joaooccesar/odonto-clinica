from django.contrib.auth.models import AbstractUser
from django.db import models
class User(AbstractUser):
    ROLES=[('admin','Administrador'),('dentist','Dentista'),('reception','Recepcionista'),('finance','Financeiro'),('inventory','Estoquista')]
    role=models.CharField('perfil',max_length=15,choices=ROLES,default='reception')
    @property
    def is_manager(self):return self.is_superuser or self.role=='admin'
    def save(self,*args,**kwargs):
        if self.is_superuser:self.role='admin'
        self.is_staff=self.is_superuser
        super().save(*args,**kwargs)
