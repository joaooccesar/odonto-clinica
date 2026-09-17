from django.contrib.auth import logout
from django.utils import timezone
from django.conf import settings
class IdleTimeoutMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        if request.user.is_authenticated:
            now=int(timezone.now().timestamp())
            if now-request.session.get('last_activity',now)>settings.SESSION_COOKIE_AGE:logout(request)
            else:request.session['last_activity']=now
        response=self.get_response(request)
        if request.user.is_authenticated:response['Cache-Control']='no-store, private'
        return response
