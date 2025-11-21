@echo off
TITLE Assistente da Casa - Instalando...
color 0A

echo ==========================================
echo      OLA! PREPARANDO O SEU SISTEMA
echo ==========================================
echo.
echo 1. Verificando se o Python esta instalado...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: O Python nao foi encontrado.
    echo Por favor, instale o Python primeiro (veja o manual).
    pause
    exit
)

echo.
echo 2. Instalando as ferramentas (isso so demora na primeira vez)...
pip install Flask Flask-SQLAlchemy Flask-Migrate Flask-Cors

echo.
echo 3. Tudo pronto! Abrindo o seu programa...
echo.
echo PODE MINIMIZAR ESTA JANELA PRETA, MAS NAO FECHE ELA!
echo.

:: Abre o navegador no Dashboard (ajuste o caminho se necessário)
start "" "frontend\dashboard.html"

:: Inicia o servidor Python
cd backend
python app.py