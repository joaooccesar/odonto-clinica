from io import BytesIO
from django.core.files.base import ContentFile,File
from django.core.files.storage import FileSystemStorage
from .crypto import cipher
class EncryptedPrivateStorage(FileSystemStorage):
    def _save(self,name,content):
        return super()._save(name,ContentFile(cipher().encrypt(content.read())))
    def _open(self,name,mode='rb'):
        with super()._open(name,'rb') as source: data=source.read()
        return File(BytesIO(cipher().decrypt(data)),name=name)
    def url(self,name): raise ValueError('Utilize o download autenticado de anexos.')
