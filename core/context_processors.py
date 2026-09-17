from accounts.permissions import allowed
NAV=[('Visão geral','layout-dashboard','/','dashboard'),('Agenda','calendar-days','/agenda/','appointments'),('Pacientes','users','/cadastros/pacientes/','patients'),('Tratamentos','clipboard-list','/cadastros/tratamentos/','treatments'),('Profissionais','stethoscope','/cadastros/profissionais/','professionals'),('Financeiro','wallet','/financeiro/','finance'),('Pagamentos','receipt','/cadastros/lancamentos/','payments'),('Estoque','package','/cadastros/materiais/','inventory'),('Compras','shopping-cart','/cadastros/compras/','purchases'),('Fornecedores','truck','/cadastros/fornecedores/','suppliers'),('Relatórios','chart-no-axes-combined','/relatorios/','reports'),('Notificações','bell','/notificacoes/','notifications'),('Configurações','settings-2','/configuracoes/','settings')]
def navigation(request):
    data={'nav_items':[{'label':a,'icon':b,'url':c,'active':request.path==c if c=='/' else request.path.startswith(c)} for a,b,c,d in NAV if allowed(request.user,d)]}
    data.update({'can_'+area:allowed(request.user,area) for area in ['clinical','finance','payments','inventory','appointments','patients','settings']})
    return data
