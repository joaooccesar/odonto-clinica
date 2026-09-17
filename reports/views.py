from django.shortcuts import render
from django.http import Http404
from accounts.permissions import require,allowed
from core.views import selected_period,filter_context
from audit.services import record
from .services import REPORTS,report_data
from .exports import export_table
@require('reports')
def index(request):
    available={k:v[0] for k,v in REPORTS.items() if allowed(request.user,v[1])};key=request.GET.get('report') or next(iter(available),None)
    if key not in available:raise Http404
    start,end,filters=selected_period(request);columns,rows=report_data(key,start,end,filters,request.user)
    if request.GET.get('format'):record('export_report',detail=key);return export_table(available[key],columns,rows,request.GET['format'])
    return render(request,'reports/index.html',{'title':'Relatórios','reports':available,'selected':key,'report_title':available[key],'columns':columns,'rows':rows[:200],'row_count':len(rows),'start':start,'end':end,**filter_context()})
