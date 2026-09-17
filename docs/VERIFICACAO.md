# Verificação da entrega

Data: 17/09/2026. Ambiente: Linux, Django 5.2.17, SQLite.

- 32 testes automatizados aprovados: `python manage.py test tests --settings=config.test_settings`.
- `python manage.py check`: nenhum problema identificado.
- `python manage.py makemigrations --check --dry-run`: sem mudanças pendentes.
- Migrations aplicadas em banco novo e arquivos estáticos coletados com sucesso.
- Demonstração criada: oito pacientes fictícios, agenda, estoque, pagamentos e prontuário.
- Backup criptografado da demonstração restaurado em outra base migrada vazia. Confirmados oito pacientes e dois registros clínicos, com leitura do conteúdo descriptografado.
- Relatórios exercitados em HTML, PDF, XLSX e CSV; proteção contra fórmulas em exportações tabulares implementada.
- Páginas e formulários testados pelo cliente HTTP do Django. Não houve inspeção visual em navegador.

Não executados neste ambiente: PostgreSQL real, Docker, instalador Windows, SMTP externo, concorrência sob carga e homologação clínica. Essas verificações permanecem necessárias antes de implantação com dados reais. Consulte ESCOPO.md para limites funcionais.
