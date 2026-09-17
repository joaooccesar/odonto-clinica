from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from audit.services import record
@transaction.atomic
def anonymize(patient,actor,reason):
    if not actor.is_manager:raise ValidationError('Apenas administradores podem anonimizar.')
    if not reason.strip():raise ValidationError('Informe uma justificativa.')
    if any([patient.appointments.exists(),patient.entries.exists(),patient.plans.exists(),patient.clinical_entries.exists(),patient.attachments.exists()]):raise ValidationError('Cadastro com histórico requer análise de retenção da clínica e não pode ser anonimizado automaticamente.')
    patient.name=f'Paciente anonimizado #{patient.pk}'
    for field in ['phone','email','address','gender','occupation','insurance','insurance_number','emergency_contact','notes']:setattr(patient,field,'')
    patient.cpf=None;patient.birth_date=None;patient.active=False;patient.reminder_consent=False;patient.privacy_acknowledged=False;patient.privacy_at=None;patient.anonymized_at=timezone.now();patient.save()
    record('anonymize',patient,reason,user=actor)
