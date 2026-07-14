# Lance la synchronisation quotidienne de la playlist YouTube.
# Utilise par la tache planifiee Windows (configurer_planification.ps1).

$ErrorActionPreference = "Continue"

$ScriptDir = $PSScriptRoot
$PythonScript = Join-Path $ScriptDir "telecharger_playlist.py"
$DownloadDir = Join-Path $env:USERPROFILE "Desktop\Musique\Download\Boumboum"
$LogDir = Join-Path $DownloadDir "logs"
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

function Test-Dependencies {
    param([string]$Python)

    $issues = @()

    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        $issues += "FFmpeg introuvable dans le PATH"
    }

    & $Python -c "import yt_dlp, mutagen" 2>$null
    if ($LASTEXITCODE -ne 0) {
        $issues += "Modules Python manquants (yt-dlp, mutagen). Lancez : pip install yt-dlp mutagen"
    }

    return $issues
}

function Remove-OldLogs {
    param([int]$Keep = 30)
    $logs = Get-ChildItem -Path $LogDir -Filter "sync_*.log" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending
    if ($logs.Count -gt $Keep) {
        $logs | Select-Object -Skip $Keep | Remove-Item -Force
    }
}

try {
    Set-Location $ScriptDir

    if (-not (Test-Path $PythonScript)) {
        throw "Script introuvable : $PythonScript"
    }

    New-Item -ItemType Directory -Force -Path $DownloadDir | Out-Null
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    Remove-OldLogs

    Write-Log "=== Demarrage synchronisation BoomBoom ==="
    Write-Log "Repertoire   : $ScriptDir"
    Write-Log "Script Python : $PythonScript"

    $python = Find-Python
    if (-not $python) {
        throw "Python introuvable. Installez Python depuis https://www.python.org/downloads/"
    }
    Write-Log "Python        : $python"

    $depIssues = Test-Dependencies -Python $python
    if ($depIssues.Count -gt 0) {
        foreach ($issue in $depIssues) {
            Write-Log "ERREUR DEP : $issue"
        }
        throw "Dependances manquantes. Corrigez les erreurs ci-dessus."
    }

    & $python $PythonScript 2>&1 | ForEach-Object {
        Write-Log "$_"
    }

    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "telecharger_playlist.py a termine avec le code $exitCode"
    }

    Write-Log "=== Synchronisation terminee avec succes ==="
    exit 0
}
catch {
    Write-Log "ERREUR : $_"
    exit 1
}
