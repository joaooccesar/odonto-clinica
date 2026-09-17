# OdontoClínica

Sistema web de gestão odontológica em Django: pacientes, prontuário, odontograma, agenda, profissionais, tratamentos, estoque, fornecedores, compras, pagamentos e relatórios. Interface em português, responsiva, com tema claro/escuro.

**Comece localmente para avaliar.** Use somente dados fictícios até validar os fluxos e preparar a implantação. Veja os limites detalhados em [docs/ESCOPO.md](docs/ESCOPO.md).

## Instalação rápida — Windows

1. Instale Python 3.12 ou 3.13 com o launcher `py` e acesso à internet para baixar dependências.
2. Extraia o ZIP e abra a pasta `odontoclinica`.
3. Execute `iniciar_windows.bat`. O script cria o ambiente, gera chaves, instala dependências, aplica migrations e solicita seu usuário administrador na primeira execução.
4. Acesse http://127.0.0.1:8000. O terminal precisa permanecer aberto. Para parar, pressione Ctrl+C.

Não existe senha padrão. Ao criar o administrador, a senha digitada não aparece no terminal.

## Instalação rápida — Linux / macOS

Python 3.12+ com módulo `venv` e pip:

```bash
cd odontoclinica
bash iniciar_linux.sh
```

Acesse http://127.0.0.1:8000. Este modo usa SQLite e servidor local de desenvolvimento. Não o exponha à internet.

## Instalação manual

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/configure.py
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

`configure.py` cria `.env` apenas quando não existe. Nunca apague as chaves para resolver um erro: prontuários, anexos e backups dependem da chave original.

## Demonstração

Em uma base sem unidades e pacientes, depois de migrar, execute:

```bash
python manage.py seed_demo
```

Pode existir um administrador criado anteriormente. O comando adiciona unidade, dentista, pacientes, materiais, consultas, pagamentos, plano e prontuário fictícios. É executado uma única vez e não sobrescreve dados. Contas `demo_*` são inativas e não têm senha; use seu administrador.

## Primeiro fluxo

1. Configurações → crie unidade e consultório, procedimentos e usuários por perfil.
2. Profissionais → vincule o usuário dentista e cadastre horários de atendimento.
3. Estoque → cadastre materiais, lotes e entrada inicial. Configure consumo por procedimento.
4. Pacientes → cadastre os dados administrativos. Um dentista adiciona anamnese e observações do odontograma.
5. Agenda → crie a consulta, confirme, inicie e conclua. A conclusão baixa estoque e gera cobrança e comissão.
6. Pagamentos → abra o título e registre pagamento parcial ou total.
7. Compras → crie pedido, adicione itens e receba. A entrada de estoque e conta a pagar acontecem juntas.
8. Relatórios → escolha período e relatório, aplique filtros e exporte.

Um plano precisa de aceite e data antes de agendar sessões vinculadas. Campos marcados com asterisco são obrigatórios. Cadastros históricos são preservados: use inativação, retificação ou estorno.

## Perfis

| Perfil | Acesso principal |
|---|---|
| Administrador | Todos os módulos; configurações e usuários |
| Dentista | Sua agenda/planos, pacientes e registros clínicos compartilhados |
| Recepção | Cadastro administrativo, agenda, planos e recebimentos de pacientes |
| Financeiro | Títulos, pagamentos, comprovantes e relatórios financeiros |
| Estoque | Materiais, lotes, movimentações, compras e fornecedores |

O Django Admin é reservado a superusuários; modelos de negócio são somente leitura para preservar as regras. Usuários comuns são gerenciados em Configurações. Para redefinir senha: `python manage.py changepassword USUARIO`.

## PostgreSQL com Docker

Instale Docker Engine/Desktop e Compose. Gere `.env` com Python antes de subir; o script usa apenas a biblioteca padrão.

```bash
python scripts/configure.py
docker compose up --build -d
docker compose exec web python manage.py createsuperuser
# Opcional, em base vazia:
docker compose exec web python manage.py seed_demo
```

O Compose usa PostgreSQL 16 e volumes persistentes para banco, anexos e backups. Porta local: http://127.0.0.1:8000. Não execute `docker compose down -v` se precisar preservar os dados.

Para PostgreSQL sem Docker, instale/crie uma base e configure `DATABASE_URL=postgresql://usuario:senha@servidor:5432/odonto` no `.env`. Percent-encode caracteres especiais de credenciais na URL. Depois migre a base.

## Implantação

O `.env` inicial é de desenvolvimento (`DEBUG=True`). Para produção, configure `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` com os domínios HTTPS e proxy TLS. Ative `TRUST_PROXY_HEADERS=True` apenas quando o proxy for confiável e sobrescrever `X-Forwarded-Proto`. Mantenha o aplicativo inacessível diretamente fora do proxy. Configure persistência, backups externos e monitoramento. Execute `python manage.py check --deploy` com o ambiente definitivo.

Não coloque chaves no código. Para atualizar, faça backup, instale dependências, execute migrations e collectstatic, e reinicie os processos. Atualizações de dependências exigem repetir testes.

## E-mail e WhatsApp

O padrão `django.core.mail.backends.console.EmailBackend` imprime o lembrete no terminal. Para envio real, configure no `.env`:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.seudominio.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=usuario
EMAIL_HOST_PASSWORD=segredo
DEFAULT_FROM_EMAIL=clinica@seudominio.com
```

O paciente precisa autorizar lembretes e ter um e-mail. Notificações → Enviar e-mail é ação manual. WhatsApp prepara mensagem para revisão no aplicativo externo; não envia automaticamente.

## Backup e restauração

Guarde uma cópia protegida do `.env` separada do backup. A chave `FIELD_ENCRYPTION_KEY` precisa ser a mesma na restauração. Backups contêm dados sensíveis, embora sejam criptografados.

Pare o servidor e todos os processos que escrevem na base. Com o banco disponível:

```bash
python manage.py backup_clinic --maintenance
# Ou destino explícito:
python manage.py backup_clinic --maintenance --output /caminho/seguro/clinica.ocbackup
```

Copie o arquivo para armazenamento externo protegido. Para restaurar, prepare **uma nova base vazia**, instale a mesma versão, configure a chave original, execute `migrate` e mantenha `private_media` vazio:

```bash
python manage.py restore_clinic /caminho/clinica.ocbackup --maintenance
```

A restauração recusa banco ou diretório de anexos já preenchidos. Verifique login, prontuários e downloads antes de reabrir. Não substitui testes periódicos de recuperação.

Em Docker: `docker compose stop web`; então `docker compose run --rm web python manage.py backup_clinic --maintenance`. Copie o backup do volume antes de retomar com `docker compose up -d web`. A restauração deve apontar a volumes/base novos e manter a chave original. Para automação de backups, programe janela de manutenção no servidor; nenhum agendamento externo vem ativado.

## Testes

Na pasta do projeto, com o ambiente ativo:

```bash
python manage.py test tests --settings=config.test_settings
python manage.py check
python manage.py makemigrations --check --dry-run
```

Testes cobrem permissões/CSRF, conflitos e recorrência, estoque FEFO e rollback, conclusão idempotente, compra, parcelas, pagamento parcial/estorno, cálculo de lucro, criptografia e relatórios nos três formatos. Verificação executada nesta entrega: SQLite em Linux. Não foi realizada validação visual em navegador nem execução de Docker/PostgreSQL/Windows/SMTP real.

## Estrutura

`accounts`, `patients`, `professionals`, `appointments`, `clinical_records`, `treatments`, `inventory`, `suppliers`, `purchases`, `finance`, `reports`, `notifications`, `audit` e `core`. Cada módulo possui modelos/migrations; regras transacionais ficam em serviços. Veja [docs/ARQUITETURA.md](docs/ARQUITETURA.md) para relações e decisões técnicas.

Arquivos `.env`, banco local, anexos, backups e ambientes virtuais não fazem parte da distribuição. O ZIP contém código, migrations, estáticos locais, testes e documentação.
