from .settings import *
DEBUG=True
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
ALLOWED_HOSTS=['testserver','localhost','127.0.0.1']
PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
STORAGES={**STORAGES,'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}}
