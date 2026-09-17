from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from accounts.permissions import require
from .models import Purchase
from .services import receive
@require('purchases')
def detail(request,pk):
    p=get_object_or_404(Purchase.objects.select_related('supplier','branch').prefetch_related('items__product'),pk=pk)
    return render(request,'purchases/detail.html',{'title':str(p),'purchase':p})
@require('purchases')
@require_POST
def receive_view(request,pk):
    p=get_object_or_404(Purchase,pk=pk)
    try:receive(p,request.user);messages.success(request,'Compra recebida. Estoque e conta a pagar atualizados.')
    except ValidationError as e:messages.error(request,' '.join(e.messages))
    return redirect('purchase_detail',pk=pk)
