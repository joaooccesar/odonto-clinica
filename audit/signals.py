from django.db.models.signals import pre_save,post_save
from django.contrib.auth.signals import user_logged_in,user_logged_out,user_login_failed
from django.dispatch import receiver
from .services import record
APPS={'accounts','patients','professionals','appointments','clinical_records','treatments','inventory','suppliers','purchases','finance','notifications'}
@receiver(pre_save)
def capture(sender,instance,raw=False,**kwargs):
    if raw or sender._meta.app_label not in APPS or not instance.pk:return
    old=sender.objects.filter(pk=instance.pk).first()
    if old:instance._changes=[f.name for f in sender._meta.fields if f.name not in {'password','last_login','updated_at'} and getattr(old,f.attname)!=getattr(instance,f.attname)]
@receiver(post_save)
def changed(sender,instance,created,raw=False,**kwargs):
    if raw or sender._meta.app_label not in APPS:return
    changes=getattr(instance,'_changes',[])
    if created or changes:record('create' if created else 'update',instance,', '.join(changes))
@receiver(user_logged_in)
def login(sender,request,user,**kwargs):record('login',user,user=user)
@receiver(user_logged_out)
def logout(sender,request,user,**kwargs):
    if user:record('logout',user,user=user)
@receiver(user_login_failed)
def failed(sender,credentials,request,**kwargs):record('login_failed')
