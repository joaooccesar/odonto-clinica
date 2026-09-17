from django.conf import settings
from django.db import models
from cryptography.fernet import Fernet
def cipher(): return Fernet(settings.FIELD_ENCRYPTION_KEY.encode())
class EncryptedTextField(models.TextField):
    def from_db_value(self,value,expression,connection):
        if value and value.startswith('fernet$'): return cipher().decrypt(value[7:].encode()).decode()
        return value
    def get_prep_value(self,value):
        value=super().get_prep_value(value)
        return 'fernet$'+cipher().encrypt(value.encode()).decode() if value else value
