from decimal import Decimal
from django import forms
from django.forms import modelform_factory
from django.contrib.auth.forms import UserCreationForm
from accounts.models import User
from appointments.models import Appointment
from clinical_records.models import ClinicalEntry,Attachment
from finance.models import Entry,METHODS
from inventory.models import Batch,Movement
class StyledForm(forms.ModelForm):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():
            field.widget.attrs['class']='form-check-input' if isinstance(field.widget,forms.CheckboxInput) else 'form-select' if isinstance(field.widget,(forms.Select,forms.SelectMultiple)) else 'form-control'
            if isinstance(field,forms.DateTimeField):
                field.widget=forms.DateTimeInput(attrs={'type':'datetime-local','class':'form-control'},format='%Y-%m-%dT%H:%M');field.input_formats=['%Y-%m-%dT%H:%M','%Y-%m-%d %H:%M:%S']
            elif isinstance(field,forms.DateField):field.widget=forms.DateInput(attrs={'type':'date','class':'form-control'},format='%Y-%m-%d')
            elif isinstance(field,forms.TimeField):field.widget=forms.TimeInput(attrs={'type':'time','class':'form-control'},format='%H:%M')
            if isinstance(field.widget,forms.Textarea):field.widget.attrs['rows']=3
class AppointmentForm(StyledForm):
    occurrences=forms.IntegerField(label='Sessões semanais (incluindo esta)',min_value=1,max_value=26,initial=1)
    class Meta:
        model=Appointment
        fields=['patient','professional','procedure','room','plan_item','start','end','value','payment_method','fit_in','fit_in_reason','notes']
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if self.instance.pk:self.fields.pop('occurrences')
        for name in ['patient','professional','procedure','room']:self.fields[name].queryset=self.fields[name].queryset.filter(active=True)
class EntryForm(StyledForm):
    installments=forms.IntegerField(label='Parcelas mensais',min_value=1,max_value=60,initial=1)
    class Meta:
        model=Entry
        fields=['direction','category','description','branch','patient','supplier','professional','procedure','cost_center','amount','discount','issue_date','due_date','method']
class ClinicalForm(StyledForm):
    class Meta:
        model=ClinicalEntry
        fields=['professional','kind','text','allergies','conditions','medicines','tooth','surface','condition','supersedes']
class AttachmentForm(StyledForm):
    class Meta:model=Attachment;fields=['title','category','file']
class PaymentForm(forms.Form):
    amount=forms.DecimalField(label='Valor',max_digits=12,decimal_places=2,min_value=Decimal(".01"),widget=forms.NumberInput(attrs={'class':'form-control','step':'.01'}))
    paid_on=forms.DateField(label='Data do pagamento',widget=forms.DateInput(attrs={'type':'date','class':'form-control'}))
    method=forms.ChoiceField(label='Forma de pagamento',choices=METHODS,widget=forms.Select(attrs={'class':'form-select'}))
    note=forms.CharField(label='Observação',required=False,max_length=250,widget=forms.TextInput(attrs={'class':'form-control'}))
class MovementForm(forms.Form):
    batch=forms.ModelChoiceField(label='Lote',queryset=Batch.objects.select_related('product'),widget=forms.Select(attrs={'class':'form-select'}))
    kind=forms.ChoiceField(label='Tipo',choices=[x for x in Movement.KINDS if x[0] not in ['procedure','purchase']],widget=forms.Select(attrs={'class':'form-select'}))
    delta=forms.DecimalField(label='Variação (+ entrada / − saída)',max_digits=12,decimal_places=3,widget=forms.NumberInput(attrs={'class':'form-control','step':'.001'}))
    reason=forms.CharField(label='Motivo',max_length=250,widget=forms.TextInput(attrs={'class':'form-control'}))
class AccountCreateForm(UserCreationForm):
    class Meta:model=User;fields=['username','first_name','last_name','email','role','password1','password2']
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():field.widget.attrs['class']='form-control'
def model_form(model,fields):return modelform_factory(model,form=StyledForm,fields=fields)
