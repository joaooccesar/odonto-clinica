from datetime import date,timedelta
from decimal import Decimal
from collections import defaultdict
from django.core.exceptions import ValidationError,PermissionDenied
from django.utils import timezone
from accounts.permissions import allowed
from appointments.models import Appointment
from appointments.services import scope
from finance.models import Entry,Payment
from inventory.models import Product,Batch,Movement
from patients.models import Patient
from purchases.models import Purchase
from treatments.models import TreatmentPlan
ZERO=Decimal('0')
def period(params):
    today=timezone.localdate()
    try:
        start=date.fromisoformat(params['from']) if params.get('from') else today.replace(day=1)
        end=date.fromisoformat(params['to']) if params.get('to') else today
    except ValueError as e:raise ValidationError('Período inválido.') from e
    if start>end or (end-start).days>3660:raise ValidationError('Use período válido de até dez anos.')
    filters={}
    for key in ['professional','procedure','branch']:
        if params.get(key):
            if not params[key].isdigit():raise ValidationError('Filtro inválido.')
            filters[key]=int(params[key])
    return start,end,filters
def filter_appointments(qs,filters):
    for key,value in filters.items():qs=qs.filter(**{('room__branch_id' if key=='branch' else key+'_id'):value})
    return qs
def filter_entries(qs,filters,prefix=''):
    for key,value in filters.items():qs=qs.filter(**{prefix+key+'_id':value})
    return qs
def finance_summary(start,end,filters):
    entries=filter_entries(Entry.objects.filter(cancelled=False).prefetch_related('payments'),filters)
    payments=list(filter_entries(Payment.objects.filter(paid_on__range=(start,end),entry__cancelled=False).select_related('entry'),filters,'entry__'))
    sessions=list(filter_appointments(Appointment.objects.filter(status='completed',completed_at__date__range=(start,end)),filters))
    income=expenses=ZERO;categories=defaultdict(lambda:ZERO);chart=defaultdict(lambda:{'income':ZERO,'expense':ZERO,'cost':ZERO})
    for p in payments:
        value=-p.amount if p.is_refund else p.amount;month=p.paid_on.strftime('%Y-%m')
        if p.entry.direction=='in':income+=value;chart[month]['income']+=value
        else:
            expenses+=value;categories[p.entry.category]+=value;chart[month]['expense']+=value
            if p.entry.category not in ['purchase','commission']:chart[month]['cost']+=value
            elif p.entry.category=='commission' and not p.entry.appointment_id:chart[month]['cost']+=value
    material=sum((a.material_cost for a in sessions),ZERO)
    other_direct=sum((a.other_direct_cost for a in sessions),ZERO)
    commission=sum((a.commission for a in sessions),ZERO)+sum(((-p.amount if p.is_refund else p.amount) for p in payments if p.entry.direction=='out' and p.entry.category=='commission' and not p.entry.appointment_id),ZERO)
    for a in sessions:chart[timezone.localdate(a.completed_at).strftime('%Y-%m')]['cost']+=a.material_cost+a.other_direct_cost+a.commission
    direct=material+other_direct+categories['direct'];overhead=categories['fixed']+categories['variable']+categories['other'];tax=categories['tax'];gross=income-direct;profit=gross-overhead-commission-tax
    receivables=[e for e in entries if e.direction=='in' and e.issue_date<=end and e.balance>0]
    paying_patients={p.entry.patient_id for p in payments if p.entry.direction=='in' and not p.is_refund and p.entry.patient_id}
    return {'income':income,'expenses':expenses,'cash':income-expenses,'billed':sum((e.amount for e in entries if e.direction=='in' and start<=e.issue_date<=end),ZERO),'material':material,'direct':direct,'overhead':overhead,'fixed':categories['fixed'],'variable':categories['variable'],'commission':commission,'tax':tax,'gross':gross,'profit':profit,'margin':profit/income*100 if income else ZERO,'outstanding':sum((e.balance for e in receivables),ZERO),'overdue':sum((e.balance for e in receivables if e.due_date<timezone.localdate()),ZERO),'ticket_patient':income/len(paying_patients) if paying_patients else ZERO,'ticket_procedure':sum((a.value for a in sessions),ZERO)/len(sessions) if sessions else ZERO,'chart':{'labels':sorted(chart),'income':[float(chart[k]['income']) for k in sorted(chart)],'expenses':[float(chart[k]['expense']) for k in sorted(chart)],'profit':[float(chart[k]['income']-chart[k]['cost']) for k in sorted(chart)]}}
REPORTS={
'appointments':('Consultas por período','appointments'),'absences':('Cancelamentos e faltas','appointments'),'patients':('Pacientes novos e recorrentes','patients'),'production':('Produção por dentista','appointments'),'procedures':('Procedimentos realizados','appointments'),'plans':('Planos de tratamento','treatments'),'finance':('Receitas e despesas','finance'),'overdue':('Contas vencidas','finance'),'profit':('Lucro e margem','finance'),'commission':('Comissões','finance'),'stock':('Estoque e sugestão de compra','inventory'),'expiry':('Validades próximas','inventory'),'movements':('Movimentações de estoque','inventory'),'purchases':('Compras por fornecedor','purchases'),'profitability':('Rentabilidade por procedimento e dentista','finance')}
def report_data(key,start,end,filters,user):
    if key not in REPORTS or not allowed(user,REPORTS[key][1]):raise PermissionDenied
    qs=scope(user,filter_appointments(Appointment.objects.select_related('patient','professional','procedure','room__branch').filter(start__date__range=(start,end)),filters))
    if key in ['appointments','absences']:
        if key=='absences':qs=qs.filter(status__in=['cancelled','missed'])
        return ['Data','Paciente','Dentista','Procedimento','Unidade','Status','Motivo'],[[timezone.localtime(a.start).strftime('%d/%m/%Y %H:%M'),a.patient.name,a.professional.name,a.procedure.name,a.room.branch.name,a.get_status_display(),a.cancellation_reason] for a in qs]
    if key in ['production','procedures','commission','profitability']:
        groups=defaultdict(lambda:[0,ZERO,ZERO,ZERO,ZERO])
        for a in qs.filter(status='completed'):
            label=a.professional.name if key in ['production','commission'] else a.procedure.name
            if key=='profitability':label+=' / '+a.professional.name
            row=groups[label];row[0]+=1;row[1]+=a.value;row[2]+=a.material_cost+a.other_direct_cost;row[3]+=a.commission;row[4]+=a.value-a.material_cost-a.other_direct_cost-a.commission
        if not allowed(user,'finance'):return ['Descrição','Sessões concluídas'],[[k,v[0]] for k,v in groups.items()]
        return ['Descrição','Sessões','Produção R$','Custos diretos R$','Comissão R$','Contribuição R$'],[[k,*v] for k,v in groups.items()]
    if key=='patients':
        seen=set(qs.values_list('patient_id',flat=True));new=Patient.objects.filter(created_at__date__range=(start,end))
        if filters or user.role=='dentist':new=new.filter(pk__in=seen)
        previous=set(Appointment.objects.filter(patient_id__in=seen,start__date__lt=start,status='completed').values_list('patient_id',flat=True))
        return ['Indicador','Pacientes'],[['Cadastrados no período',new.count()],['Com consulta no período',len(seen)],['Recorrentes (atendimento anterior)',len(previous)]]
    if key=='plans':
        plans=TreatmentPlan.objects.select_related('patient','professional').prefetch_related('items').filter(created_at__date__range=(start,end))
        if user.role=='dentist':plans=plans.filter(professional__user=user)
        if filters.get('professional'):plans=plans.filter(professional_id=filters['professional'])
        if filters.get('procedure'):plans=plans.filter(items__procedure_id=filters['procedure']).distinct()
        if filters.get('branch'):plans=plans.filter(patient_id__in=qs.values('patient_id'))
        return ['Paciente','Plano','Dentista','Status','Total R$'],[[a.patient.name,a.name,a.professional.name,a.get_status_display(),a.total] for a in plans]
    if key in ['finance','overdue']:
        entries=filter_entries(Entry.objects.filter(cancelled=False).prefetch_related('payments'),filters);rows=[]
        for e in entries:
            if key=='finance' and not start<=e.issue_date<=end:continue
            if key=='overdue' and not(e.due_date<timezone.localdate() and e.balance>0):continue
            rows.append([e.description,e.get_direction_display(),e.get_category_display(),e.due_date.isoformat(),e.net,e.paid,e.balance,e.status])
        return ['Descrição','Tipo','Categoria','Vencimento','Líquido R$','Pago R$','Saldo R$','Status'],rows
    if key=='profit':
        s=finance_summary(start,end,filters)
        return ['Indicador','Valor'],[[label,s[k]] for label,k in [('Faturamento bruto','billed'),('Receita recebida','income'),('Saídas de caixa','expenses'),('Materiais consumidos','material'),('Custos diretos totais','direct'),('Despesas operacionais','overhead'),('Comissões','commission'),('Impostos','tax'),('Lucro bruto gerencial','gross'),('Lucro líquido gerencial','profit'),('Margem %','margin'),('Ticket por paciente pagante','ticket_patient'),('Ticket por sessão','ticket_procedure')]]
    if key=='stock':return ['Material','Código','Unidade','Saldo','Mínimo','Sugestão de compra','Valor R$'],[[p.name,p.code,p.unit,p.quantity,p.minimum,p.suggestion,p.stock_value] for p in Product.objects.filter(active=True).prefetch_related('batches')]
    if key=='expiry':return ['Material','Lote','Validade','Saldo'],[[b.product.name,b.number,b.expiry.isoformat(),b.quantity] for b in Batch.objects.select_related('product').filter(quantity__gt=0,expiry__lte=end+timedelta(days=30)).order_by('expiry')]
    if key=='movements':return ['Data','Material','Lote','Tipo','Variação','Saldo após','Responsável'],[[timezone.localtime(m.created_at).strftime('%d/%m/%Y %H:%M'),m.batch.product.name,m.batch.number,m.get_kind_display(),m.delta,m.balance_after,str(m.actor or 'Sistema')] for m in Movement.objects.select_related('batch__product','actor').filter(created_at__date__range=(start,end))]
    purchases=Purchase.objects.select_related('supplier').prefetch_related('items').filter(order_date__range=(start,end))
    if filters.get('branch'):purchases=purchases.filter(branch_id=filters['branch'])
    return ['Pedido','Fornecedor','Data','Status','Total R$'],[[x.pk,str(x.supplier),x.order_date.isoformat(),x.get_status_display(),x.total] for x in purchases]
