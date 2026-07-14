# Lance la synchronisation quotidienne de la playlist YouTube.
# Utilise par la tache planifiee Windows (configurer_planification.ps1).

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$PythonScript = Join-Path $ScriptDir "telecharger_playlist.py"
$LogDir = Join-Path $env:USERPROFILE "Desktop\Musique\Download\Boumboum\logs"
$LogFile = Join-Path $LogDir ("sync_{0:yyyy-MM-dd_HH-mm-ss}.log" -f (Get-Date))

function Write-Log {
    param([string]$Message)
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $Message
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Find-Python {
    foreach ($cmd in @("py", "python", "python3")) {
        $exe = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($exe) {
            return $exe.Source
        }
    }
    return $null
}

try {
    if (-not (Test-Path $PythonScript)) {
        throw "Script introuvable : $PythonScript"
    }

    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    Write-Log "=== Demarrage synchronisation BoomBoom ==="
    Write-Log "Script Python : $PythonScript"

    $python = Find-Python
    if (-not $python) {
        throw "Python introuvable. Installez Python depuis https://www.python.org/downloads/"
    }
    Write-Log "Python        : $python"

    $output = & $python $PythonScript 2>&1
    foreach ($line in $output) {
        Write-Log $line
    }

    if ($LASTEXITCODE -ne 0) {
        throw "telecharger_playlist.py a termine avec le code $LASTEXITCODE"
    }

    Write-Log "=== Synchronisation terminee avec succes ==="
    exit 0
}
catch {
    Write-Log "ERREUR : $_"
    exit 1
}
