# Tailwind CSS 빌드 (Windows PowerShell 5.1+) — Node 없이 standalone CLI 를 쓴다 (ARCHITECTURE.md §15).
# macOS / Linux 는 scripts/tailwind.sh 를 사용한다. 동작은 동일하다.
#
# 사용 (프로젝트 루트에서):
#   .\scripts\tailwind.ps1           최소화 빌드 (배포·커밋 전)
#   .\scripts\tailwind.ps1 -Watch    개발 중 변경 감시
#
# CLI 는 처음 한 번 .tools\ 에 내려받고, scripts\tailwind-sha256sums.txt 의 SHA-256 과 맞을 때만 쓴다.
# 입력: app\static\css\input.css → 출력: app\static\css\app.css (.gitignore 대상)
param([switch]$Watch)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
# 경로는 모두 -LiteralPath 로 다룬다 — 프로젝트 경로에 [ ] 가 있으면 -Path 는 와일드카드로 해석해 실패한다.

$versionLine = Get-Content -LiteralPath (Join-Path $Root 'scripts\versions.env') | Where-Object { $_ -match '^TAILWIND_VERSION=' } | Select-Object -First 1
if (-not $versionLine) { throw 'scripts\versions.env 에 TAILWIND_VERSION 이 없습니다.' }
$Version = ($versionLine -replace '^TAILWIND_VERSION=', '').Trim()

if ($env:PROCESSOR_ARCHITECTURE -ne 'AMD64' -and $env:PROCESSOR_ARCHITEW6432 -ne 'AMD64') {
    throw "Tailwind CSS standalone CLI 는 Windows x64 만 제공됩니다 (현재: $env:PROCESSOR_ARCHITECTURE)."
}
$Asset = 'tailwindcss-windows-x64.exe'
$ToolsDir = Join-Path $Root '.tools'
$Bin = Join-Path $ToolsDir "tailwindcss-$Version-windows-x64.exe"

if (-not (Test-Path -LiteralPath $Bin)) {
    $expected = $null
    foreach ($line in Get-Content -LiteralPath (Join-Path $Root 'scripts\tailwind-sha256sums.txt')) {
        $parts = $line -split '\s+'
        if ($parts.Count -ge 2 -and $parts[1] -eq $Asset) { $expected = $parts[0].ToLowerInvariant() }
    }
    if (-not $expected) { throw "tailwind-sha256sums.txt 에 $Asset 항목이 없습니다." }

    New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null
    # 내려받기는 시스템 임시 폴더에서 한다 — PS 5.1 의 Invoke-WebRequest -OutFile 은 경로의 [ ] 를 와일드카드로 해석한다.
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("tailwindcss-" + [guid]::NewGuid().ToString("N") + ".download")
    Write-Host "Tailwind CSS v$Version ($Asset) 내려받는 중…"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/tailwindlabs/tailwindcss/releases/download/v$Version/$Asset" -OutFile $tmp
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $tmp).Hash.ToLowerInvariant()
    if ($actual -ne $expected) {
        Remove-Item -Force -LiteralPath $tmp
        throw "SHA-256 불일치 — 내려받은 파일을 쓰지 않습니다 (기대 $expected, 실제 $actual)."
    }
    Move-Item -Force -LiteralPath $tmp -Destination $Bin
}

$cssArgs = @('-i', (Join-Path $Root 'app\static\css\input.css'), '-o', (Join-Path $Root 'app\static\css\app.css'))
if ($Watch) {
    & $Bin @cssArgs --watch
} else {
    & $Bin @cssArgs --minify
}
exit $LASTEXITCODE
