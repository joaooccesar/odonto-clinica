from .context import actor
from .models import AuditLog
def record(action,obj=None,detail='',user=None):
    return AuditLog.objects.create(actor=user or actor.get(),action=action,model=obj._meta.label_lower if obj is not None else 'session',object_id=str(obj.pk) if obj is not None else '',detail=detail[:300])
