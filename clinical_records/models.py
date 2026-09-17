import hashlib
import uuid
from pathlib import Path
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from core.models import Immutable
from core.crypto import EncryptedTextField
def upload_path(instance,filename):return f'patient/{instance.patient_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'
def validate_file(value):
    if value.size>10*1024*1024:raise ValidationError('Tamanho máximo: 10 MB.')
    ext=Path(value.name).suffix.lower()
    if ext not in ['.pdf','.png','.jpg','.jpeg']:raise ValidationError('Use PDF, JPG ou PNG.')
    pos=value.tell();head=value.read(10);value.seek(0)
    try:
        if ext=='.pdf':
            if not head.startswith(b'%PDF-'):raise ValueError()
        else:
            from PIL import Image
            image=Image.open(value);image.verify()
            if image.format not in ['PNG','JPEG']:raise ValueError()
    except Exception as e:raise ValidationError('Conteúdo do arquivo inválido.') from e
    finally:value.seek(pos)
class ClinicalEntry(Immutable):
    KINDS=[('anamnesis','Anamnese'),('evolution','Evolução'),('diagnosis','Diagnóstico'),('prescription','Prescrição / orientação'),('certificate','Atestado / declaração'),('tooth','Odontograma'),('correction','Retificação')]
    patient=models.ForeignKey('patients.Patient',on_delete=models.PROTECT,related_name='clinical_entries',verbose_name='paciente')
    professional=models.ForeignKey('professionals.Professional',on_delete=models.PROTECT,verbose_name='dentista responsável')
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,editable=False)
    kind=models.CharField('tipo',max_length=20,choices=KINDS)
    text=EncryptedTextField('registro clínico')
    allergies=EncryptedTextField('alergias',blank=True)
    conditions=EncryptedTextField('doenças preexistentes',blank=True)
    medicines=EncryptedTextField('medicamentos em uso',blank=True)
    tooth=models.CharField('dente (FDI)',max_length=2,blank=True)
    surface=models.CharField('face / região',max_length=40,blank=True)
    condition=models.CharField('condição',max_length=20,blank=True,choices=[('healthy','Hígido'),('caries','Cárie'),('restored','Restaurado'),('missing','Ausente'),('planned','Tratamento indicado'),('treated','Tratado')])
    supersedes=models.ForeignKey('self',on_delete=models.PROTECT,null=True,blank=True,related_name='corrections',verbose_name='retifica registro')
    digest=models.CharField(max_length=64,editable=False)
    created_at=models.DateTimeField(auto_now_add=True)
    def clean(self):
        valid=[str(q*10+i) for q in range(1,5) for i in range(1,9)]+[str(q*10+i) for q in range(5,9) for i in range(1,6)]
        if self.tooth and self.tooth not in valid:raise ValidationError('Use um dente válido pela numeração FDI.')
        if self.kind=='tooth' and not(self.tooth and self.condition):raise ValidationError('Selecione dente e condição.')
        if self.supersedes_id and self.supersedes.patient_id!=self.patient_id:raise ValidationError('A retificação deve pertencer ao mesmo paciente.')
        if self.actor_id and self.actor.role=='dentist' and self.professional.user_id!=self.actor_id:raise ValidationError('O autor deve ser o profissional autenticado.')
    def save(self,*args,**kwargs):
        values=[self.patient_id,self.professional_id,self.actor_id,self.kind,self.text,self.allergies,self.conditions,self.medicines,self.tooth,self.surface,self.condition,self.supersedes_id]
        self.digest=hashlib.sha256('|'.join(str(v) for v in values).encode()).hexdigest()
        return super().save(*args,**kwargs)
    class Meta:ordering=['-created_at'];verbose_name='registro clínico'
class Attachment(Immutable):
    patient=models.ForeignKey('patients.Patient',on_delete=models.PROTECT,related_name='attachments',verbose_name='paciente')
    title=models.CharField('título',max_length=180)
    category=models.CharField('tipo',max_length=20,choices=[('clinical','Clínico'),('document','Administrativo'),('receipt','Comprovante')])
    file=models.FileField('arquivo',upload_to=upload_path,validators=[validate_file])
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,editable=False)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:ordering=['-created_at'];verbose_name='anexo'
