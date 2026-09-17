import io,json,zipfile,hashlib,tempfile,shutil
from pathlib import Path,PurePosixPath
from django.conf import settings
from django.apps import apps
from django.db import transaction
from django.core.management import call_command
from django.core.management.base import BaseCommand,CommandError
from cryptography.fernet import InvalidToken
from core.crypto import cipher
class Command(BaseCommand):
    help='Restaura em banco migrado vazio e diretório de anexos vazio, com a mesma chave.'
    def add_arguments(self,parser):
        parser.add_argument('file');parser.add_argument('--maintenance',action='store_true')
    def handle(self,*args,**options):
        if not options['maintenance']:raise CommandError('Pare a aplicação e informe --maintenance.')
        for model in apps.get_models():
            if model._meta.app_label not in ['auth','contenttypes','sessions','admin'] and model.objects.exists():raise CommandError('Restauração exige banco sem dados da clínica. Use uma base nova e migre antes.')
        from django.contrib.auth.models import Group
        if Group.objects.exists():raise CommandError('A base de destino contém grupos. Use uma base nova.')
        root=Path(settings.MEDIA_ROOT)
        if root.exists() and any(root.iterdir()):raise CommandError('O diretório private_media deve estar vazio.')
        try:payload=cipher().decrypt(Path(options['file']).read_bytes())
        except InvalidToken as e:raise CommandError('Backup inválido ou chave incorreta.') from e
        with zipfile.ZipFile(io.BytesIO(payload)) as z,tempfile.TemporaryDirectory() as tmp:
            manifest=json.loads(z.read('manifest.json'))
            if manifest.get('version')!=1:raise CommandError('Versão de backup incompatível.')
            for name,digest in manifest['files'].items():
                relative=PurePosixPath(name)
                if relative.is_absolute() or '..' in relative.parts or not(name=='data.json' or name.startswith('media/')):raise CommandError('Caminho inválido no backup.')
                content=z.read(name)
                if hashlib.sha256(content).hexdigest()!=digest:raise CommandError('Integridade inválida.')
                target=Path(tmp).joinpath(*relative.parts);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
            if not(Path(tmp)/'data.json').exists():raise CommandError('Backup sem dados.')
            try:
                with transaction.atomic():
                    call_command('loaddata',str(Path(tmp)/'data.json'),verbosity=0)
                    if (Path(tmp)/'media').exists():shutil.copytree(Path(tmp)/'media',root,dirs_exist_ok=True)
            except Exception:
                if root.exists():shutil.rmtree(root)
                raise
        self.stdout.write(self.style.SUCCESS('Restauração concluída. Valide acessos e anexos antes de reabrir a aplicação.'))
