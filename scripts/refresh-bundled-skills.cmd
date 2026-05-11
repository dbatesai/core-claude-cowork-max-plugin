@echo off
REM Thin Windows shim — execs the cross-platform Python entry.
python "%~dp0refresh_bundled_skills.py" %*
