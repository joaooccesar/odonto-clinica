import io,json,zipfile,hashlib
from pathlib import Path
from datetime import datetime
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand,CommandError
from core.crypto import cipher
class Command(BaseCommand):
    help='Backup lógico criptografado. Pare os processos da aplicação antes de executar.'
    def add_arguments(self,parser):
        parser.add_argument('--maintenance',action='store_true',help='Confirma que os processos que escrevem dados estão parados.')
        parser.add_argument('--output')
    def handle(self,*args,**options):
        if not options['maintenance']:raise CommandError('Pare os processos da aplicação e informe --maintenance.')
        output=Path(options['output'] or settings.BASE_DIR/'backups'/f'clinica-{datetime.now():%Y%m%d-%H%M%S}.ocbackup').resolve()
        if output.exists():raise CommandError('O destino já existe.')
        data=io.StringIO();call_command('dumpdata',natural_foreign=True,exclude=['contenttypes','auth.permission','sessions.session','admin.logentry'],stdout=data)
        payload=io.BytesIO();manifest={}
        with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as z:
            def add(name,content):z.writestr(name,content);manifest[name]=hashlib.sha256(content).hexdigest()
            add('data.json',data.getvalue().encode())
            root=Path(settings.MEDIA_ROOT)
            if root.exists():
                for f in root.rglob('*'):
                    if f.is_file() and not f.is_symlink():add('media/'+f.relative_to(root).as_posix(),f.read_bytes())
            z.writestr('manifest.json',json.dumps({'version':1,'files':manifest}))
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('xb') as f:f.write(cipher().encrypt(payload.getvalue()))
        output.chmod(0o600);self.stdout.write(self.style.SUCCESS(f'Backup criado: {output}. Guarde a chave FIELD_ENCRYPTION_KEY separadamente.'))
