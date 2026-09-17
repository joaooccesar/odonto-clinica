from .context import actor
class AuditMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        token=actor.set(request.user if request.user.is_authenticated else None)
        try:return self.get_response(request)
        finally:actor.reset(token)
