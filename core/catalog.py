from dataclasses import dataclass
from django.apps import apps
@dataclass
class Resource:
    model_name:str
    title:str
    area:str
    fields:list
    columns:list
    search:list
    edit_roles:tuple=('admin',)
    kind:str=''
    @property
    def model(self):return apps.get_model(self.model_name)
R=Resource
RESOURCES={
'pacientes':R('patients.Patient','Pacientes','patients',['name','cpf','birth_date','phone','email','address','gender','occupation','insurance','insurance_number','emergency_contact','notes','privacy_acknowledged','reminder_consent','active'],[('Paciente','name'),('Telefone','phone'),('Convênio','insurance'),('Ativo','active')],['name','cpf','phone','email'],('admin','dentist','reception'),'patient'),
'profissionais':R('professionals.Professional','Profissionais','professionals',['user','name','specialty','cro','phone','email','commission_percent','commission_fixed','active'],[('Nome','name'),('Especialidade','specialty'),('CRO','cro'),('Ativo','active')],['name','specialty','cro']),
'horarios':R('professionals.Availability','Horários de atendimento','professionals',['professional','weekday','start_time','end_time'],[('Dentista','professional'),('Dia','get_weekday_display'),('Início','start_time'),('Fim','end_time')],['professional__name']),
'bloqueios':R('professionals.ScheduleBlock','Bloqueios e férias','professionals',['professional','start','end','reason'],[('Dentista','professional'),('Início','start'),('Fim','end'),('Motivo','reason')],['professional__name','reason'],('admin','dentist')),
'consultorios':R('professionals.Room','Consultórios','settings',['name','branch','active'],[('Nome','name'),('Unidade','branch'),('Ativo','active')],['name','branch__name']),
'unidades':R('core.Branch','Unidades','settings',['name','address','active'],[('Unidade','name'),('Endereço','address'),('Ativa','active')],['name']),
'procedimentos':R('treatments.Procedure','Procedimentos','treatments',['name','category','description','duration','price','estimated_cost','specialty','sessions','professionals','active'],[('Procedimento','name'),('Categoria','category'),('Minutos','duration'),('Preço','price')],['name','category']),
'consumo':R('treatments.ProcedureMaterial','Materiais por procedimento','inventory',['procedure','product','quantity'],[('Procedimento','procedure'),('Material','product'),('Quantidade / sessão','quantity')],['procedure__name','product__name'],('admin','inventory')),
'tratamentos':R('treatments.TreatmentPlan','Planos de tratamento','treatments',['patient','professional','name','status','discount','payment_method','installments','acceptance','accepted_at'],[('Plano','name'),('Paciente','patient'),('Dentista','professional'),('Status','get_status_display'),('Total','total')],['name','patient__name'],('admin','dentist','reception'),'plan'),
'itens-tratamento':R('treatments.PlanItem','Sessões do tratamento','treatments',['plan','procedure','teeth','sessions','price'],[('Plano','plan'),('Procedimento','procedure'),('Dentes','teeth'),('Previstas','sessions'),('Concluídas','completed_sessions')],['plan__patient__name','procedure__name'],('admin','dentist','reception')),
'materiais':R('inventory.Product','Estoque de materiais','inventory',['name','category','code','barcode','unit','minimum','maximum','manufacturer','supplier','location','active'],[('Material','name'),('Código','code'),('Saldo','quantity'),('Mínimo','minimum'),('Valor em estoque','stock_value')],['name','code','barcode'],('admin','inventory'),'product'),
'lotes':R('inventory.Batch','Lotes e validades','inventory',['product','number','expiry','unit_cost'],[('Material','product'),('Lote','number'),('Validade','expiry'),('Saldo','quantity'),('Custo unitário','unit_cost')],['product__name','number'],('admin','inventory')),
'movimentacoes':R('inventory.Movement','Movimentações de estoque','inventory',[],[('Data','created_at'),('Lote','batch'),('Tipo','get_kind_display'),('Variação','delta'),('Saldo após','balance_after'),('Responsável','actor')],['batch__product__name','batch__number','reason'],(),'readonly'),
'fornecedores':R('suppliers.Supplier','Fornecedores','suppliers',['name','trade_name','cnpj','contact','phone','email','address','products','payment_terms','active'],[('Fornecedor','name'),('Contato','contact'),('Telefone','phone'),('E-mail','email')],['name','trade_name','cnpj'],('admin','inventory')),
'compras':R('purchases.Purchase','Pedidos de compra','purchases',['supplier','branch','order_date','expected_date','due_date','invoice_number','payment_method','status'],[('Pedido','id'),('Fornecedor','supplier'),('Entrega prevista','expected_date'),('Status','get_status_display'),('Total','total')],['supplier__name','invoice_number'],('admin','inventory'),'purchase'),
'itens-compra':R('purchases.PurchaseItem','Itens do pedido','purchases',['purchase','product','quantity','unit_cost','batch_number','expiry'],[('Pedido','purchase'),('Material','product'),('Quantidade','quantity'),('Lote','batch_number'),('Custo','unit_cost')],['product__name','batch_number'],('admin','inventory')),
'lancamentos':R('finance.Entry','Contas e pagamentos','payments',[],[('Descrição','description'),('Tipo','get_direction_display'),('Vencimento','due_date'),('Valor líquido','net'),('Saldo','balance'),('Status','status')],['description','patient__name','supplier__name'],('admin','finance','reception'),'entry'),
'usuarios':R('accounts.User','Usuários e acessos','settings',['username','first_name','last_name','email','role','is_active'],[('Usuário','username'),('Nome','first_name'),('Perfil','get_role_display'),('Ativo','is_active')],['username','first_name','email'],('admin',),'user'),
'auditoria':R('audit.AuditLog','Trilha de auditoria','audit',[],[('Data','created_at'),('Usuário','actor'),('Ação','action'),('Entidade','model'),('ID','object_id'),('Campos / detalhe','detail')],['action','model','actor__username'],(),'readonly'),
}
