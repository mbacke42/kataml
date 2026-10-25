@echo off
REM Lance KataML. Seul prerequis : uv (https://docs.astral.sh/uv/).
where uv >nul 2>nul || (echo uv est introuvable. Installation : powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex" & exit /b 1)
cd /d "%~dp0"
uv run --project "%~dp0." python -m kataml %*
