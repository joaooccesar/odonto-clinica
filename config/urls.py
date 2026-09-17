from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth
from accounts.views import ClinicLoginView
from core import views as c
from patients import views as p
from appointments import views as a
from clinical_records import views as cr
from finance import views as f
from inventory import views as i
from purchases import views as pu
from reports import views as r
from notifications import views as n
urlpatterns=[path('admin/',admin.site.urls),path('entrar/',ClinicLoginView.as_view(template_name='registration/login.html'),name='login'),path('sair/',auth.LogoutView.as_view(),name='logout'),path('senha/',auth.PasswordChangeView.as_view(template_name='core/form.html',success_url='/'),name='password_change'),path('',c.dashboard,name='dashboard'),path('busca/',c.search),path('privacidade/',c.privacy),path('configuracoes/',c.settings_page),path('cadastros/<slug:resource>/',c.resource_list),path('cadastros/<slug:resource>/novo/',c.resource_form),path('cadastros/<slug:resource>/<int:pk>/editar/',c.resource_form),path('pacientes/<int:pk>/',p.detail,name='patient_detail'),path('pacientes/<int:pk>/anonimizar/',p.anonymize_view),path('pacientes/<int:pk>/registro/',cr.add),path('pacientes/<int:pk>/anexo/',cr.upload),path('anexos/<int:pk>/',cr.download),path('documentos/<int:pk>/',cr.document),path('agenda/',a.calendar),path('agenda/nova/',a.form),path('agenda/eventos/',a.events),path('agenda/horarios/',a.slots),path('agenda/<int:pk>/',a.detail,name='appointment_detail'),path('agenda/<int:pk>/editar/',a.form),path('agenda/<int:pk>/status/',a.status),path('agenda/<int:pk>/mover/',a.move),path('financeiro/',f.dashboard),path('financeiro/lancamento/<int:pk>/',f.detail,name='entry_detail'),path('financeiro/lancamento/<int:pk>/cancelar/',f.cancel_view),path('financeiro/pagamento/<int:pk>/estornar/',f.refund_view),path('estoque/movimentar/',i.movement),path('compras/<int:pk>/',pu.detail,name='purchase_detail'),path('compras/<int:pk>/receber/',pu.receive_view),path('relatorios/',r.index),path('notificacoes/',n.index),path('notificacoes/<int:pk>/email/',n.email_reminder)]
