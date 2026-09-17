from pathlib import Path
import secrets
import base64
root = Path(__file__).resolve().parents[1]
target = root / '.env'
if target.exists():
    print('.env preservado; nenhuma chave foi alterada.')
else:
    content = (root / '.env.example').read_text(encoding='utf-8')
    content = content.replace('SECRET_KEY=GENERATE', 'SECRET_KEY=' + secrets.token_urlsafe(64))
    content = content.replace('FIELD_ENCRYPTION_KEY=GENERATE', 'FIELD_ENCRYPTION_KEY=' + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
    content += '\nPOSTGRES_USER=odonto\nPOSTGRES_DB=odonto\nPOSTGRES_PASSWORD=' + secrets.token_urlsafe(32) + '\n'
    target.write_text(content, encoding='utf-8')
    target.chmod(0o600)
    print('.env criado. Guarde uma cópia segura para restaurar os dados criptografados.')
