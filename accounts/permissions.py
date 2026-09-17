from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
ACCESS={
 'dashboard':{'admin','dentist','reception','finance','inventory'},
 'patients':{'admin','dentist','reception'}, 'appointments':{'admin','dentist','reception'},
 'professionals':{'admin','dentist','reception'}, 'clinical':{'admin','dentist'},
 'treatments':{'admin','dentist','reception'}, 'finance':{'admin','finance'},
 'payments':{'admin','finance','reception'}, 'inventory':{'admin','inventory'},
 'suppliers':{'admin','inventory','finance'}, 'purchases':{'admin','inventory'},
 'settings':{'admin'}, 'audit':{'admin'},
 'reports':{'admin','dentist','reception','finance','inventory'},
 'notifications':{'admin','dentist','reception','finance','inventory'},
}
def allowed(user,area):
    return user.is_authenticated and user.is_active and (user.is_manager or user.role in ACCESS.get(area,set()))
def require(area):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request,*args,**kwargs):
            if not allowed(request.user,area):raise PermissionDenied
            return view(request,*args,**kwargs)
        return wrapped
    return decorator
