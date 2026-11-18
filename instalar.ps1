# Instala lo necesario para los tutoriales de Alexia en Windows 10/11.
# Uso: doble clic en instalar.bat  (o: powershell -ExecutionPolicy Bypass -File instalar.ps1)
# Se puede correr las veces que haga falta: lo que ya está instalado se salta.
param([switch]$SinPausa)   # Claude lo corre con -SinPausa
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Start-Transcript -Path "$PSScriptRoot\instalar.log" -Force | Out-Null

function Paso($t) { Write-Host "`n== $t" -ForegroundColor Cyan }
function Falla($t) {
    Write-Host "`nNO SE PUDO TERMINAR: $t" -ForegroundColor Red
    Write-Host "Mandale el archivo instalar.log a quien te ayuda con la herramienta (o pegalo en Claude)." -ForegroundColor Yellow
    Stop-Transcript | Out-Null; if (-not $SinPausa) { Read-Host "Enter para cerrar" }; exit 1
}
function RecargarPath {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
function BuscarPython {
    # Evita el "python" falso de la Microsoft Store (carpeta WindowsApps), que no es Python.
    $candidatos = @(
        (Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object FullName)
        (Get-ChildItem "$env:ProgramFiles\Python3*\python.exe" -ErrorAction SilentlyContinue | ForEach-Object FullName)
        (Get-Command python -All -ErrorAction SilentlyContinue | Where-Object Source -notmatch 'WindowsApps' | ForEach-Object Source)
    ) | Where-Object { $_ }
    foreach ($c in $candidatos) {
        $v = & $c --version 2>&1
        if ($v -match 'Python 3\.(1[0-9])') { return $c }
    }
    return $null
}
function WingetInstalar($id, $nombre) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Falla "falta winget (Instalador de aplicaciones de Windows). Instalalo desde Microsoft Store ('Instalador de aplicación') o instalá $nombre a mano."
    }
    winget install --id $id -e --scope user --accept-package-agreements --accept-source-agreements --silent
    if ($LASTEXITCODE -ne 0) {
        # Algunos paquetes no tienen instalador por usuario: se reintenta sin --scope (puede pedir permiso de administrador).
        winget install --id $id -e --accept-package-agreements --accept-source-agreements --silent
    }
    RecargarPath
}

Paso "1/5 Python 3"
$py = BuscarPython
if (-not $py) {
    WingetInstalar 'Python.Python.3.13' 'Python 3.13 (https://www.python.org/downloads/, marcar "Add python.exe to PATH")'
    $py = BuscarPython
    if (-not $py) { Falla "Python no quedó instalado." }
}
Write-Host "Python: $py"

Paso "2/5 ffmpeg (arma el video)"
$ffmpegWinget = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe" -ErrorAction SilentlyContinue
if ((Get-Command ffmpeg -ErrorAction SilentlyContinue) -or $ffmpegWinget) { Write-Host "ffmpeg ya está instalado" }
else { WingetInstalar 'Gyan.FFmpeg' 'ffmpeg (https://www.gyan.dev/ffmpeg/builds/)' }

Paso "3/5 Git (lo usa Claude Code en Windows y sirve para actualizar la herramienta)"
if (Get-Command git -ErrorAction SilentlyContinue) { git --version }
else { WingetInstalar 'Git.Git' 'Git para Windows (https://git-scm.com/download/win)' }

Paso "4/5 Librerías de Python"
& $py -m pip install --user --upgrade pip
& $py -m pip install --user -r requirements.txt
if ($LASTEXITCODE -ne 0) { Falla "pip no pudo instalar las librerías (¿sin internet o detrás de un proxy?)." }

Paso "5/5 Navegador para Playwright"
& $py -m playwright install chromium
if ($LASTEXITCODE -ne 0) { Falla "no se pudo descargar Chromium para Playwright (¿proxy o antivirus?)." }

Paso "Verificación"
& $py tutor.py voces --filtro es-CL
if ($LASTEXITCODE -ne 0) { Falla "la prueba de voz no respondió (edge-tts necesita internet)." }

Write-Host "`nTodo listo." -ForegroundColor Green
Write-Host "Si Claude ya estaba abierto, cerralo y abrilo de nuevo para que encuentre Python." -ForegroundColor Green
Write-Host "Después: app de Claude > pestaña Code > abrir esta carpeta > escribir /nuevo-tutorial" -ForegroundColor Green
Stop-Transcript | Out-Null
if (-not $SinPausa) { Read-Host "Enter para cerrar" }
