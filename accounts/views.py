import hashlib
from datetime import timedelta
from django.contrib.auth.views import LoginView
from django.utils import timezone
from django.db.models import F
from core.models import LoginAttempt
class ClinicLoginView(LoginView):
    template_name='registration/login.html'
    def post(self,request,*args,**kwargs):
        key=hashlib.sha256((request.META.get('REMOTE_ADDR','')+'|'+request.POST.get('username','').casefold()).encode()).hexdigest()
        self.attempt,_=LoginAttempt.objects.get_or_create(key=key,defaults={'since':timezone.now()})
        if self.attempt.since<timezone.now()-timedelta(minutes=15):
            self.attempt.count=0;self.attempt.since=timezone.now();self.attempt.save()
        if self.attempt.count>=5:
            form=self.get_form();form.is_valid();form.add_error(None,'Muitas tentativas. Aguarde 15 minutos.')
            return self.render_to_response(self.get_context_data(form=form),status=429)
        return super().post(request,*args,**kwargs)
    def form_invalid(self,form):
        LoginAttempt.objects.filter(pk=self.attempt.pk).update(count=F('count')+1)
        return super().form_invalid(form)
    def form_valid(self,form):
        self.attempt.delete();return super().form_valid(form)
