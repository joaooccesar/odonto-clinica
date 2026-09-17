@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe scripts\configure.py
if errorlevel 1 goto fail
.venv\Scripts\python.exe manage.py migrate
if errorlevel 1 goto fail
.venv\Scripts\python.exe manage.py collectstatic --noinput
if errorlevel 1 goto fail
.venv\Scripts\python.exe manage.py shell -c "from accounts.models import User; import sys; sys.exit(0 if User.objects.filter(is_superuser=True,is_active=True).exists() else 1)"
if errorlevel 1 .venv\Scripts\python.exe manage.py createsuperuser
if errorlevel 1 goto fail
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
goto end
:fail
echo Falha na instalacao. Consulte a mensagem acima e o README.md.
pause
:end
endlocal
