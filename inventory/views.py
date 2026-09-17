from django.shortcuts import render,redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from accounts.permissions import require
from core.forms import MovementForm
from core.views import form_error
from .services import move
@require('inventory')
def movement(request):
    form=MovementForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        try:move(actor=request.user,**form.cleaned_data);messages.success(request,'Estoque atualizado e movimentação registrada.');return redirect('resource_list',resource='movimentacoes')
        except ValidationError as e:form_error(form,e)
    return render(request,'core/form.html',{'title':'Movimentar estoque','form':form,'back':'/cadastros/materiais/','hint':'Informe a variação: quantidade positiva para entrada e negativa para saída. Saldo negativo não é permitido.'})
