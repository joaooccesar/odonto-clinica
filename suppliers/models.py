from django.db import models
from core.models import Timestamped
class Supplier(Timestamped):
    name=models.CharField('razão social',max_length=150)
    trade_name=models.CharField('nome fantasia',max_length=150,blank=True)
    cnpj=models.CharField('CNPJ',max_length=18,blank=True)
    contact=models.CharField('contato',max_length=100,blank=True)
    phone=models.CharField('telefone',max_length=25,blank=True)
    email=models.EmailField('e-mail',blank=True)
    address=models.TextField('endereço',blank=True)
    products=models.TextField('produtos fornecidos',blank=True)
    payment_terms=models.CharField('condições de pagamento',max_length=200,blank=True)
    active=models.BooleanField('ativo',default=True)
    def __str__(self):return self.trade_name or self.name
    class Meta:ordering=['name'];verbose_name='fornecedor';verbose_name_plural='fornecedores'
