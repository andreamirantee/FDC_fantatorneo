param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExe
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}

Write-Host "[1/4] Creating virtual environment with $PythonExe"
& $PythonExe -m venv .venv
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create virtual environment. Ensure selected Python includes the 'venv' module."
}

Write-Host "[2/4] Upgrading pip"
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip."
}

Write-Host "[3/4] Installing dependencies"
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed."
}

Write-Host "[4/4] Running tests"
& .\.venv\Scripts\python.exe -m pytest tests\test_api.py
if ($LASTEXITCODE -ne 0) {
    throw "Tests failed after environment setup."
}

Write-Host "Environment ready."