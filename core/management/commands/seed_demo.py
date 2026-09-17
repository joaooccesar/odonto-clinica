from datetime import timedelta,datetime,time
from decimal import Decimal
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from django.utils import timezone
from accounts.models import User
from core.models import Branch
from professionals.models import Professional,Room,Availability
from patients.models import Patient
from treatments.models import Procedure,ProcedureMaterial,TreatmentPlan,PlanItem
from inventory.models import Product,Batch
from inventory.services import move
from appointments.models import Appointment
from appointments.services import save_appointment,transition
from finance.models import Entry
from finance.services import pay
from suppliers.models import Supplier
from clinical_records.models import ClinicalEntry
class Command(BaseCommand):
    help='Insere dados fictícios uma única vez. Não cria senhas de acesso.'
    @transaction.atomic
    def handle(self,*args,**options):
        if Patient.objects.exists() or Branch.objects.exists():raise CommandError('Use uma base sem pacientes e unidades para a demonstração.')
        actor=User.objects.create_user(username='demo_sistema',role='admin',is_active=False);actor.set_unusable_password();actor.save()
        branch=Branch.objects.create(name='Clínica demonstração',address='Endereço fictício')
        room=Room.objects.create(name='Consultório 01',branch=branch)
        dentist=User.objects.create_user(username='demo_dentista',role='dentist',first_name='Marina',is_active=False);dentist.set_unusable_password();dentist.save()
        pro=Professional.objects.create(name='Marina · demonstração',specialty='Clínica geral',cro='DEMO-001',user=dentist,commission_percent=Decimal('20'))
        for day in range(7):Availability.objects.create(professional=pro,weekday=day,start_time=time(7),end_time=time(20))
        supplier=Supplier.objects.create(name='Fornecedor fictício',email='fornecedor@example.invalid')
        product=Product.objects.create(name='Kit descartável demonstrativo',category='Descartáveis',code='DEMO-KIT',unit='kit',minimum=Decimal('10'),maximum=Decimal('100'),supplier=supplier)
        batch=Batch.objects.create(product=product,number='DEMO-001',expiry=timezone.localdate()+timedelta(days=180),unit_cost=Decimal('8'))
        move(batch,100,'entry','Saldo inicial demonstrativo',actor)
        procedures=[]
        for name,price,cost in [('Avaliação',150,5),('Profilaxia',240,12),('Restauração',380,30)]:
            proc=Procedure.objects.create(name=name,category='Clínica geral',price=Decimal(price),estimated_cost=Decimal(cost),duration=45)
            ProcedureMaterial.objects.create(procedure=proc,product=product,quantity=Decimal('1'));procedures.append(proc)
        names=['Ana Exemplo','Bruno Exemplo','Carla Exemplo','Diego Exemplo','Elisa Exemplo','Felipe Exemplo','Gabriela Exemplo','Henrique Exemplo']
        patients=[Patient.objects.create(name=name,email=f'paciente{i}@example.invalid',privacy_acknowledged=True,privacy_at=timezone.now(),reminder_consent=False) for i,name in enumerate(names)]
        today=timezone.localdate()
        for day in range(-14,5):
            for slot in range(2):
                proc=procedures[(day+slot)%3];patient=patients[(day+slot)%8];start=timezone.make_aware(datetime.combine(today+timedelta(days=day),time(9+slot*2)))
                a=Appointment(patient=patient,professional=pro,procedure=proc,room=room,start=start,end=start+timedelta(minutes=45),value=proc.price,payment_method='pix')
                save_appointment(a,actor);transition(a.pk,'confirmed',actor)
                if day<0:
                    transition(a.pk,'completed',actor)
                    Appointment.objects.filter(pk=a.pk).update(completed_at=start+timedelta(minutes=45))
                    e=Entry.objects.get(appointment=a,direction='in');e.issue_date=start.date();e.due_date=start.date();e.save()
                    if day%4:pay(e,e.net,start.date(),'pix',actor)
        ClinicalEntry.objects.create(patient=patients[0],professional=pro,actor=actor,kind='anamnesis',text='Registro fictício para demonstração.',allergies='Não informadas no exemplo.')
        ClinicalEntry.objects.create(patient=patients[0],professional=pro,actor=actor,kind='tooth',text='Exemplo de observação por dente.',tooth='16',condition='planned')
        plan=TreatmentPlan.objects.create(patient=patients[0],professional=pro,name='Plano demonstrativo',status='accepted',acceptance='Aceite fictício de demonstração',accepted_at=timezone.now())
        PlanItem.objects.create(plan=plan,procedure=procedures[2],sessions=2,price=procedures[2].price,teeth='16, 26')
        expense=Entry.objects.create(direction='out',category='fixed',description='Despesa fixa demonstrativa',branch=branch,amount=Decimal('900'),due_date=today)
        pay(expense,expense.amount,today,'pix',actor)
        self.stdout.write(self.style.SUCCESS('Demonstração criada. Crie seu acesso com python manage.py createsuperuser. Contas demo não têm senha e estão inativas.'))
