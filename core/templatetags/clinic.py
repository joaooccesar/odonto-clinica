from datetime import datetime,date,time
from decimal import Decimal
from django import template
from django.utils import timezone
register=template.Library()
@register.filter
def money(value):
    try:return 'R$ '+f'{Decimal(str(value)):,.2f}'.replace(',','X').replace('.',',').replace('X','.')
    except Exception:return 'R$ 0,00'
@register.filter
def display(value):
    if value is None or value=='':return '—'
    if isinstance(value,bool):return 'Sim' if value else 'Não'
    if isinstance(value,datetime):return timezone.localtime(value).strftime('%d/%m/%Y %H:%M')
    if isinstance(value,date):return value.strftime('%d/%m/%Y')
    if isinstance(value,time):return value.strftime('%H:%M')
    if isinstance(value,Decimal):return f'{value:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
    return value
@register.simple_tag(takes_context=True)
def querystring(context,**kwargs):
    query=context['request'].GET.copy()
    for key,value in kwargs.items():query[key]=value
    return query.urlencode()
