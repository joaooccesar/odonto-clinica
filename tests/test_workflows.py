from datetime import timedelta,datetime,time
from decimal import Decimal as D
from io import BytesIO
from tempfile import TemporaryDirectory
from pathlib import Path
from django.test import TestCase,Client,override_settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.utils import timezone
from accounts.models import User
from core.models import Branch
from professionals.models import Professional,Room,Availability,ScheduleBlock
from patients.models import Patient
from treatments.models import Procedure,ProcedureMaterial,TreatmentPlan,PlanItem
from inventory.models import Product,Batch,Movement
from inventory.services import move
from appointments.models import Appointment
from appointments.services import save_appointment,transition,reschedule
from finance.models import Entry,Payment
from finance.services import pay,refund,create_entry
from suppliers.models import Supplier
from purchases.models import Purchase,PurchaseItem
from purchases.services import receive
from clinical_records.models import ClinicalEntry,Attachment
from reports.services import REPORTS,finance_summary
from core.catalog import RESOURCES
class Workflows(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin=User.objects.create_user('admin',password='test-only-password',role='admin')
        cls.dentist=User.objects.create_user('dentist',password='test-only-password',role='dentist')
        cls.reception=User.objects.create_user('reception',role='reception')
        cls.finance=User.objects.create_user('finance',role='finance')
        cls.inventory=User.objects.create_user('inventory',role='inventory')
        cls.branch=Branch.objects.create(name='Unidade de teste')
        cls.room=Room.objects.create(name='Sala 1',branch=cls.branch)
        cls.pro=Professional.objects.create(name='Dentista',specialty='Geral',cro='TESTE',user=cls.dentist,commission_percent=D('10'))
        for day in range(7):Availability.objects.create(professional=cls.pro,weekday=day,start_time=time(7),end_time=time(20))
        cls.patient=Patient.objects.create(name='Paciente teste')
        cls.proc=Procedure.objects.create(name='Profilaxia',category='Geral',price=D('200'),estimated_cost=D('5'))
        cls.product=Product.objects.create(name='Material',category='Descartável',code='TEST',minimum=D('5'))
        cls.batch=Batch.objects.create(product=cls.product,number='A',unit_cost=D('3'),expiry=timezone.localdate()+timedelta(days=10))
        move(cls.batch,D('10'),'entry','Inicial',cls.admin)
        ProcedureMaterial.objects.create(procedure=cls.proc,product=cls.product,quantity=D('2'))
    def appointment(self,days=-1,hour=9,**extra):
        start=timezone.make_aware(datetime.combine(timezone.localdate()+timedelta(days=days),time(hour)))
        kw=dict(patient=self.patient,professional=self.pro,room=self.room,procedure=self.proc,start=start,end=start+timedelta(minutes=30),value=D('200'),payment_method='pix');kw.update(extra)
        return save_appointment(Appointment(**kw),self.admin)[0]
    def completed(self):
        a=self.appointment();transition(a.pk,'confirmed',self.admin);return transition(a.pk,'completed',self.admin)
    def test_completion_stock_finance_and_idempotence(self):
        a=self.completed();self.batch.refresh_from_db();self.assertEqual(self.batch.quantity,D('8'));self.assertEqual(a.material_cost,D('6'));self.assertEqual(a.commission,D('20'));self.assertEqual(Entry.objects.filter(appointment=a).count(),2)
        transition(a.pk,'completed',self.admin);self.assertEqual(Movement.objects.filter(appointment=a).count(),1)
    def test_insufficient_stock_rolls_back(self):
        move(self.batch,-9,'manual','Saída',self.admin);a=self.appointment();transition(a.pk,'confirmed',self.admin)
        with self.assertRaises(ValidationError):transition(a.pk,'completed',self.admin)
        self.batch.refresh_from_db();a.refresh_from_db();self.assertEqual(self.batch.quantity,D('1'));self.assertEqual(a.status,'confirmed');self.assertFalse(Entry.objects.exists())
    def test_negative_stock_rejected(self):
        with self.assertRaises(ValidationError):move(self.batch,-11,'manual','Saída',self.admin)
    def test_expired_stock_not_consumed(self):
        self.batch.expiry=timezone.localdate()-timedelta(days=1);self.batch.save();a=self.appointment();transition(a.pk,'confirmed',self.admin)
        with self.assertRaises(ValidationError):transition(a.pk,'completed',self.admin)
    def test_fefo(self):
        later=Batch.objects.create(product=self.product,number='B',expiry=timezone.localdate()+timedelta(days=30),unit_cost=D('8'));move(later,5,'entry','Inicial',self.admin);self.completed();later.refresh_from_db();self.assertEqual(later.quantity,D('5'))
    def test_conflict(self):
        self.appointment()
        with self.assertRaises(ValidationError):self.appointment()
    def test_patient_conflict_other_professional(self):
        a=self.appointment();pro=Professional.objects.create(name='Outro',specialty='Geral',cro='OUTRO');room=Room.objects.create(name='Sala2',branch=self.branch)
        with self.assertRaises(ValidationError):self.appointment(professional=pro,room=room,fit_in=True,fit_in_reason='Extra')
    def test_reschedule_conflict_preserves_time(self):
        a=self.appointment(hour=9);b=self.appointment(hour=10)
        with self.assertRaises(ValidationError):reschedule(b.pk,a.start,a.end,self.admin)
        b.refresh_from_db();self.assertEqual(timezone.localtime(b.start).hour,10)
    def test_recurrence_atomic(self):
        a=self.appointment(days=7);start=a.start-timedelta(weeks=1);candidate=Appointment(patient=self.patient,professional=self.pro,room=self.room,procedure=self.proc,start=start,end=start+timedelta(minutes=30),value=D('200'))
        with self.assertRaises(ValidationError):save_appointment(candidate,self.admin,2)
        self.assertEqual(Appointment.objects.count(),1)
    def test_block_conflict(self):
        a=self.appointment()
        with self.assertRaises(ValidationError):ScheduleBlock.objects.create(professional=self.pro,start=a.start,end=a.end,reason='Férias')
    def test_outside_hours(self):
        with self.assertRaises(ValidationError):self.appointment(hour=22)
    def test_future_completion(self):
        a=self.appointment(days=2);transition(a.pk,'confirmed',self.admin)
        with self.assertRaises(ValidationError):transition(a.pk,'completed',self.admin)
    def test_cancellation_requires_reason(self):
        a=self.appointment()
        with self.assertRaises(ValidationError):transition(a.pk,'cancelled',self.admin)
        transition(a.pk,'cancelled',self.admin,'Solicitação do paciente');self.appointment()
    def test_installments_preserve_cents(self):
        entries=create_entry(Entry(direction='in',category='service',description='Parcelas',branch=self.branch,amount=D('100'),discount=D('1'),due_date=timezone.localdate()),3)
        self.assertEqual(sum(e.net for e in entries),D('99'));self.assertEqual(len(entries),3)
    def test_partial_payment_refund(self):
        a=self.completed();e=Entry.objects.get(appointment=a,direction='in');p=pay(e,D('80'),timezone.localdate(),'pix',self.admin);refund(p,D('30'),self.admin,'Ajuste');self.assertEqual(e.balance,D('150'))
        with self.assertRaises(ValidationError):refund(p,D('60'),self.admin,'Excesso')
    def test_overpayment(self):
        a=self.completed();e=Entry.objects.get(appointment=a,direction='in')
        with self.assertRaises(ValidationError):pay(e,D('201'),timezone.localdate(),'pix',self.admin)
    def test_profit_excludes_purchase_cash_double_count(self):
        a=self.completed();e=Entry.objects.get(appointment=a,direction='in');pay(e,D('200'),timezone.localdate(),'pix',self.admin)
        purchase=Entry.objects.create(direction='out',category='purchase',description='Estoque',branch=self.branch,amount=D('100'),due_date=timezone.localdate());pay(purchase,D('100'),timezone.localdate(),'pix',self.admin)
        commission=Entry.objects.get(appointment=a,direction='out');pay(commission,D('20'),timezone.localdate(),'pix',self.admin)
        s=finance_summary(timezone.localdate(),timezone.localdate(),{});self.assertEqual(s['profit'],D('169'));self.assertEqual(s['cash'],D('80'))
    def test_purchase_receipt_idempotent(self):
        sup=Supplier.objects.create(name='Fornecedor');today=timezone.localdate();p=Purchase.objects.create(supplier=sup,branch=self.branch,order_date=today,expected_date=today,due_date=today)
        PurchaseItem.objects.create(purchase=p,product=self.product,quantity=D('4'),unit_cost=D('3'),batch_number='C')
        receive(p,self.admin);receive(p,self.admin);self.assertEqual(Entry.objects.filter(purchase=p).count(),1);self.assertEqual(Batch.objects.get(number='C').quantity,D('4'))
    def test_clinical_encrypted_immutable(self):
        r=ClinicalEntry.objects.create(patient=self.patient,professional=self.pro,actor=self.admin,kind='evolution',text='Segredo clínico')
        with connection.cursor() as c:c.execute('SELECT text FROM clinical_records_clinicalentry WHERE id=%s',[r.pk]);raw=c.fetchone()[0]
        self.assertNotIn('Segredo',raw);r.refresh_from_db();self.assertEqual(r.text,'Segredo clínico')
        with self.assertRaises(ValidationError):r.save()
    def test_invalid_tooth(self):
        with self.assertRaises(ValidationError):ClinicalEntry.objects.create(patient=self.patient,professional=self.pro,actor=self.admin,kind='tooth',tooth='99',condition='caries',text='Teste')
    def test_attachment_encrypted_and_permission(self):
        with TemporaryDirectory() as d,override_settings(MEDIA_ROOT=d):
            f=SimpleUploadedFile('teste.pdf',b'%PDF-1.4 test document',content_type='application/pdf');a=Attachment.objects.create(patient=self.patient,actor=self.admin,title='Teste',category='clinical',file=f)
            self.assertNotIn(b'%PDF',Path(a.file.path).read_bytes());self.client.force_login(self.reception);self.assertEqual(self.client.get(f'/anexos/{a.pk}/').status_code,403)
            self.client.force_login(self.admin);response=self.client.get(f'/anexos/{a.pk}/');self.assertEqual(response.status_code,200);self.assertIn(b'%PDF',b''.join(response.streaming_content))
    def test_permissions(self):
        for user,paths in [(self.reception,['/financeiro/','/cadastros/materiais/','/cadastros/usuarios/',f'/pacientes/{self.patient.pk}/registro/']),(self.finance,['/agenda/','/cadastros/pacientes/']),(self.inventory,['/financeiro/',f'/pacientes/{self.patient.pk}/'])]:
            self.client.force_login(user)
            for path in paths:
                with self.subTest(user=user.username,path=path):self.assertEqual(self.client.get(path).status_code,403)
    def test_dentist_other_schedule_hidden(self):
        a=self.appointment();other=User.objects.create_user('other',role='dentist');self.client.force_login(other);self.assertEqual(self.client.get(f'/agenda/{a.pk}/').status_code,404)
    def test_login_required(self):self.assertRedirects(self.client.get('/'),'/entrar/?next=/',fetch_redirect_response=False)
    def test_csrf_required(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.admin);self.assertEqual(client.post('/cadastros/pacientes/novo/',{'name':'Teste'}).status_code,403)
    def test_pages_and_forms(self):
        self.client.force_login(self.admin);a=self.appointment()
        paths=['/','/agenda/','/agenda/nova/',f'/agenda/{a.pk}/',f'/pacientes/{self.patient.pk}/',f'/pacientes/{self.patient.pk}/registro/','/financeiro/','/notificacoes/','/configuracoes/','/busca/?q=teste','/privacidade/','/estoque/movimentar/']
        paths += [f'/cadastros/{key}/' for key in RESOURCES]
        paths += [f'/cadastros/{key}/novo/' for key,r in RESOURCES.items() if r.edit_roles]
        for path in paths:
            with self.subTest(path=path):self.assertEqual(self.client.get(path).status_code,200)
    def test_reports_all_formats(self):
        self.completed();self.client.force_login(self.admin)
        for key in REPORTS:
            for fmt in ['', 'csv','xlsx','pdf']:
                with self.subTest(report=key,fmt=fmt):self.assertEqual(self.client.get('/relatorios/',{'report':key,'format':fmt}).status_code,200)
    def test_patient_form_save(self):
        self.client.force_login(self.admin);r=self.client.post('/cadastros/pacientes/novo/',{'name':'Pessoa fictícia','active':'on','privacy_acknowledged':'on'});self.assertEqual(r.status_code,302);self.assertTrue(Patient.objects.get(name='Pessoa fictícia').privacy_at)
    def test_slots_and_events(self):
        a=self.appointment();self.client.force_login(self.admin);self.assertEqual(len(self.client.get('/agenda/eventos/').json()),1)
        r=self.client.get('/agenda/horarios/',{'date':timezone.localdate().isoformat(),'professional':self.pro.pk,'room':self.room.pk,'duration':30});self.assertEqual(r.status_code,200);self.assertGreater(len(r.json()['slots']),0)
    def test_login_rate_limit(self):
        for i in range(5):self.client.post('/entrar/',{'username':'admin','password':'wrong'})
        self.assertEqual(self.client.post('/entrar/',{'username':'admin','password':'wrong'}).status_code,429)

    def test_form_workflow(self):
        self.client.force_login(self.admin)
        start=timezone.make_aware(datetime.combine(timezone.localdate()-timedelta(days=1),time(14)))
        r=self.client.post('/agenda/nova/',{'patient':self.patient.pk,'professional':self.pro.pk,'procedure':self.proc.pk,'room':self.room.pk,'start':start.strftime('%Y-%m-%dT%H:%M'),'end':(start+timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M'),'value':'200.00','payment_method':'pix','occurrences':'1'})
        self.assertEqual(r.status_code,302);a=Appointment.objects.get()
        for status in ['confirmed','completed']:self.assertEqual(self.client.post(f'/agenda/{a.pk}/status/',{'status':status}).status_code,302)
        e=Entry.objects.get(appointment=a,direction='in');self.assertEqual(self.client.get(f'/financeiro/lancamento/{e.pk}/').status_code,200)
        r=self.client.post(f'/financeiro/lancamento/{e.pk}/',{'amount':'50.00','paid_on':timezone.localdate().isoformat(),'method':'pix','note':'Parcial'})
        self.assertEqual(r.status_code,302);self.assertEqual(e.balance,D('150'))
    def test_backup_is_encrypted_and_restore_requires_empty_target(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        from core.crypto import cipher
        import zipfile,io
        ClinicalEntry.objects.create(patient=self.patient,professional=self.pro,actor=self.admin,kind='evolution',text='Segredo de backup')
        with TemporaryDirectory() as d:
            path=Path(d)/'backup.ocbackup';call_command('backup_clinic',maintenance=True,output=str(path),stdout=io.StringIO())
            self.assertNotIn(b'Segredo',path.read_bytes())
            with zipfile.ZipFile(io.BytesIO(cipher().decrypt(path.read_bytes()))) as z:self.assertIn('Segredo de backup',z.read('data.json').decode())
            with self.assertRaises(CommandError):call_command('restore_clinic',str(path),maintenance=True)
