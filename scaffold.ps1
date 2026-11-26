#requires -Version 5.1
<#
.SYNOPSIS
  flask-starter 신규 프로젝트 스캐폴드 (ARCHITECTURE.md 준수).

.DESCRIPTION
  skeleton/ 골격을 복사하고 토큰을 치환한 뒤,
  .env 생성, 의존성 설치(venv·pip), psql 로 DB 생성, Alembic 으로 테이블 생성(upgrade head),
  Tailwind CSS 빌드까지 한 번에 수행한다.
  마지막에 flask run 실행 방법을 출력한다. Node·pnpm 은 필요 없다.

  이름 규칙: ASCII 영문자·숫자로 시작하고 영문자·숫자·공백·'_'·'-' 만 쓴다(최대 64자).
  대상 폴더: 비어 있지 않으면 대화형은 y/N 확인, 비대화형은 중단한다.
             템플릿 저장소 자신·그 하위·그 상위 폴더는 항상 거부한다.

  종료 코드: 0 = 모든 단계 완료
             1 = 중단(입력 오류, 대상 폴더 거부, 런타임 미충족, 복사·치환 실패, .env 생성·권한 제한 실패)
             2 = 골격은 생성됐지만 일부 단계(pip·DB·alembic·CSS 빌드 등)가 미완료 — 마지막 요약 참고

.PARAMETER Name
  프로젝트 이름. 없으면 묻는다.

.PARAMETER Target
  생성 위치. 기본은 템플릿 폴더의 부모 폴더 아래 <이름>.

.PARAMETER SkipDb
  psql DB 생성 + alembic 마이그레이션을 생략한다.

.PARAMETER SkipInstall
  venv/pip 설치 + alembic + Tailwind CSS 빌드를 생략한다.

.PARAMETER DbHost
  DB 접속 정보 기본값(-DbHost/-DbPort/-DbUser/-DbPassword/-DbName 공통).
  대화형이면 Enter 로 수락하고, 비밀번호는 지정하면 묻지 않는다.
  값 규칙: DB 이름은 영문자·숫자·'_'(63자 이하), 호스트는 호스트 이름·IPv4(영문자·숫자·'.'·'-'·'_') 또는 [IPv6],
  사용자는 제어 문자·큰따옴표 금지, 포트는 1~65535. 어기면 중단한다(scaffold.sh 와 같다).

.PARAMETER DbPassword
  DB 비밀번호. ⚠️ 명령줄 인자는 프로세스 목록·셸 기록에 남으므로 경고를 낸다(호환용으로만 남긴다).
  비밀번호는 환경변수 SCAFFOLD_DB_PASSWORD 로 넘기는 것을 권장한다 — 둘 다 있으면 인자가 우선한다.

.EXAMPLE
  .\scaffold.ps1 -Name project_test -Target P:\flask\project_test

.EXAMPLE
  .\scaffold.ps1 -Name Demo -Target P:\tmp\Demo -SkipDb -SkipInstall

.EXAMPLE
  .\scaffold.ps1 -Name Demo -DbUser app
  # 비대화형(CI 등)이면 비밀번호를 CI 비밀값·비밀 저장소에서 환경변수 SCAFFOLD_DB_PASSWORD 로 주입한다.
  # 대화형이면 지정하지 않고 화면에 보이지 않는 입력 프롬프트로 넣는다.
#>
[CmdletBinding()]
param(
  [string]$Name,
  [string]$Target,
  [switch]$SkipDb,
  [switch]$SkipInstall,
  [string]$DbHost = "localhost",
  [int]$DbPort = 5432,
  [string]$DbUser = "postgres",
  [string]$DbPassword,
  [string]$DbName
)

$ErrorActionPreference = "Stop"
# 한글 메시지가 콘솔에서 깨지지 않도록 출력 인코딩을 UTF-8 로 (Windows PowerShell 5.1 대응)
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

# ---------- 템플릿 설정 ----------
# 토큰을 치환할 파일 확장자 (대소문자 구분, scaffold.sh 와 동일)
$TokenExtensions = @('.py', '.html', '.css', '.js', '.md', '.ini', '.mako', '.example', '.txt', '.toml', '.sh', '.conf', '.service')
$AppPort = 5000
# 골격 복사·토큰 치환에서 제외하는 산출물 (scaffold.sh 와 동일)
#   .tools = 내려받은 Tailwind CLI, uploads·logs = 실행 산출물, app.css = Tailwind 빌드 결과
$CopyExcludeDirs  = @('.venv', 'venv', '.ruff_cache', '.pytest_cache', '__pycache__', '.tools', 'uploads', 'logs')
$CopyExcludeFiles = @('app.css', '.DS_Store', '.env')
$PruneDirs        = @('.venv', 'venv', '.ruff_cache', '.pytest_cache', '__pycache__', '.git', '.tools', 'uploads', 'logs')
# 완료 안내의 배포 전 주의
$DeployNote = @'
  ⛔ 배포 전 이 계정의 비밀번호를 바꾸고 SEED_DEFAULT_ADMIN=false, APP_ENV=production,
     COOKIE_SECURE=true(HTTPS) 로 설정하세요.
'@
# ---------- 템플릿 설정 끝 ----------

$TemplateDir = [System.IO.Path]::GetFullPath($PSScriptRoot)
$SkeletonDir = Join-Path $TemplateDir "skeleton"
$Enc = [System.Text.UTF8Encoding]::new($false)

function Write-Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }
function Write-Ok($m)   { Write-Host "  [OK] $m" -ForegroundColor Green }
function Write-Warn2($m){ Write-Host "  [!]  $m" -ForegroundColor Yellow }
function Stop-Scaffold($m) {
  Write-Host "  [X]  $m" -ForegroundColor Red
  exit 1
}

# 미완료 단계 모음 — 마지막에 요약하고, 하나라도 있으면 종료 코드 2 로 끝낸다 (scaffold.sh 와 동일).
$script:Incomplete = [System.Collections.Generic.List[string]]::new()
function Add-Incomplete([string]$m) { [void]$script:Incomplete.Add($m) }

# 비대화형 호스트(CI·-NonInteractive)에서 Read-Host 예외로 즉사하지 않도록 감싼다 (scaffold.sh 의 [ -t 0 ] 대응)
function Read-HostSafe([string]$prompt) {
  try { return Read-Host $prompt } catch { return "" }
}

# 대화형 여부 판정 (scaffold.sh 의 [ -t 0 ] 대응) — 입력이 리다이렉트/파이프면 비대화형으로 본다.
# 판정 불가 시 안전하게 비대화형($false)으로 처리해 재입력 프롬프트에서 멈추지 않도록 한다.
function Test-Interactive {
  try { return ([Environment]::UserInteractive -and -not [Console]::IsInputRedirected) } catch { return $false }
}

# $child 가 $parent 와 같거나 그 하위 경로인가 (대소문자 무시 — Windows 파일 시스템 기준)
function Test-PathWithin([string]$child, [string]$parent) {
  $c = $child.TrimEnd('\', '/'); $p = $parent.TrimEnd('\', '/')
  if ($c.Equals($p, [StringComparison]::OrdinalIgnoreCase)) { return $true }
  return $c.StartsWith($p + '\', [StringComparison]::OrdinalIgnoreCase)
}

# 링크(정션·심볼릭 링크)를 푼 실제 경로 (scaffold.sh 의 _canon_path·pwd -P 대응).
# ⛔ GetFullPath 는 링크를 풀지 않는다 — 템플릿을 가리키는 정션을 대상으로 주면 "템플릿 안인가" 검사를 통과해 버린다.
#    존재하는 가장 가까운 상위 폴더를 GetFinalPathNameByHandle 로 풀고, 아직 없는 나머지 경로를 붙인다.
#    PS 5.1(.NET Framework)에는 링크를 푸는 API 가 없어 kernel32 를 직접 부른다. 풀지 못하면 검사를 약하게 하지 않고 중단한다.
$_nativeSrc = @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;
public static class ScaffoldRealPath {
  [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
  static extern SafeFileHandle CreateFileW(string name, uint access, uint share, IntPtr sec, uint disposition, uint flags, IntPtr template);
  [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
  static extern uint GetFinalPathNameByHandleW(SafeFileHandle handle, StringBuilder buffer, uint size, uint flags);
  public static string Get(string path) {
    // 접근 권한 0 + FILE_FLAG_BACKUP_SEMANTICS(0x02000000) = 폴더 핸들, OPEN_EXISTING(3), 공유 읽기·쓰기·삭제(7)
    using (SafeFileHandle h = CreateFileW(path, 0, 7, IntPtr.Zero, 3, 0x02000000, IntPtr.Zero)) {
      if (h.IsInvalid) { throw new Win32Exception(Marshal.GetLastWin32Error()); }
      StringBuilder sb = new StringBuilder(1024);
      uint n = GetFinalPathNameByHandleW(h, sb, (uint)sb.Capacity, 0);
      if (n >= sb.Capacity) { sb = new StringBuilder((int)n + 1); n = GetFinalPathNameByHandleW(h, sb, (uint)sb.Capacity, 0); }
      if (n == 0) { throw new Win32Exception(Marshal.GetLastWin32Error()); }
      string s = sb.ToString();
      if (s.StartsWith(@"\\?\UNC\")) { return @"\\" + s.Substring(8); }
      if (s.StartsWith(@"\\?\")) { return s.Substring(4); }
      return s;
    }
  }
}
'@
function Resolve-RealPath([string]$path) {
  if (-not ('ScaffoldRealPath' -as [type])) {
    try { Add-Type -TypeDefinition $_nativeSrc -ErrorAction Stop }
    catch { Stop-Scaffold "경로의 링크를 해석할 수 없습니다(Add-Type 실패) — 중단합니다: $($_.Exception.Message)" }
  }
  $p = [System.IO.Path]::GetFullPath($path)
  $rest = New-Object System.Collections.Generic.List[string]
  while (-not [System.IO.Directory]::Exists($p)) {
    $trim = $p.TrimEnd('\', '/')
    $parent = [System.IO.Path]::GetDirectoryName($trim)
    if (-not $parent) { Stop-Scaffold "경로를 해석할 수 없습니다(존재하는 상위 폴더 없음): $path" }
    $rest.Insert(0, [System.IO.Path]::GetFileName($trim))
    $p = $parent
  }
  try { $real = [ScaffoldRealPath]::Get($p) }
  catch { Stop-Scaffold "경로의 링크를 해석할 수 없습니다 — 중단합니다: $p ($($_.Exception.Message))" }
  foreach ($r in $rest) { $real = [System.IO.Path]::Combine($real, $r) }
  $real = $real.TrimEnd('\', '/')
  if ($real -match '^[A-Za-z]:$') { $real += '\' }
  return $real
}

# 파일 접근 권한을 현재 사용자 단독으로 제한한다 (scaffold.sh 의 chmod 600 대응).
# ⛔ 경로에 [ ] 가 있어도 동작하도록 -LiteralPath 를 쓴다(-Path 는 와일드카드로 해석해 조용히 실패한다).
#    DACL 만 담은 새 FileSecurity 를 .NET 으로 쓴다 — Set-Acl 은 소유자·감사(SACL) 구역까지 쓰려다
#    이미 보호 ACL 이 걸린 파일(예: 이전 실행이 만든 .env 의 백업)에서 SeSecurityPrivilege 오류로 실패한다.
function Set-OwnerOnlyAcl([string]$path) {
  $acl = New-Object System.Security.AccessControl.FileSecurity
  $acl.SetAccessRuleProtection($true, $false)   # 상속 끊기, 상속 ACE 복사 안 함
  $acl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule(
    [System.Security.Principal.WindowsIdentity]::GetCurrent().User, 'FullControl', 'Allow')))
  if ([System.IO.File].GetMethod('SetAccessControl', [type[]]@([string], [System.Security.AccessControl.FileSecurity]))) {
    [System.IO.File]::SetAccessControl($path, $acl)            # Windows PowerShell 5.1 (.NET Framework)
  } else {
    Set-Acl -LiteralPath $path -AclObject $acl                 # PowerShell 7 (.NET 에 File.SetAccessControl 없음)
  }
}

# 최소 버전 로드 (단일 출처 versions.env — Enable-VersionManagers 에서도 쓰므로 먼저 읽는다)
$_Bootstrap   = Join-Path $TemplateDir 'skeleton\scripts\bootstrap.ps1'
$_VersionsEnv = Join-Path $TemplateDir 'skeleton\scripts\versions.env'
$_min = @{}
if (Test-Path -LiteralPath $_VersionsEnv) {
  Get-Content -LiteralPath $_VersionsEnv | ForEach-Object {
    if ($_ -match '^\s*([A-Z_]+)\s*=\s*([0-9.]+)') { $_min[$matches[1]] = $matches[2] }
  }
}

# psql 활성화 — Windows PostgreSQL 설치 관리자는 bin 을 PATH 에 넣지 않는다.
# 설치돼 있는데도 "psql 없음"으로 DB 단계를 건너뛰는 일을 막기 위해 표준 경로를 탐색해
# 현재 세션 PATH 에 추가한다. 여러 메이저가 설치돼 있으면 가장 높은 버전을 쓴다.
function Enable-Psql {
  if (Get-Command psql -ErrorAction SilentlyContinue) { return }
  $roots = @(
    "$env:ProgramFiles\PostgreSQL",
    "${env:ProgramFiles(x86)}\PostgreSQL",
    "$env:LOCALAPPDATA\Programs\PostgreSQL"
  ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
  $cand = foreach ($r in $roots) {
    Get-ChildItem -LiteralPath $r -Directory -ErrorAction SilentlyContinue | ForEach-Object {
      $exe = Join-Path $_.FullName 'bin\psql.exe'
      if (Test-Path -LiteralPath $exe) {
        $n = 0; [void][int]::TryParse(($_.Name -replace '[^0-9].*$',''), [ref]$n)
        [pscustomobject]@{ Ver = $n; Bin = (Split-Path $exe -Parent) }
      }
    }
  }
  $best = $cand | Sort-Object Ver -Descending | Select-Object -First 1
  if ($best) {
    $env:Path = "$($best.Bin);$env:Path"
    Write-Ok "psql 을 PATH 에서 찾지 못해 설치 경로를 사용합니다: $($best.Bin)"
  }
}

# ---------- 1. 이름·생성 위치 (런타임 설치보다 먼저 검증해 잘못된 입력이면 아무것도 하지 않고 끝낸다) ----------
Write-Step "신규 프로젝트 스캐폴드"
# DB 비밀번호 — ⚠️ 명령줄 인자는 프로세스 목록·셸 기록에 남는다. 환경변수 SCAFFOLD_DB_PASSWORD 를 권장하고,
# 인자는 호환용으로만 받는다(둘 다 있으면 인자 우선, 빈 값은 지정하지 않은 것으로 본다 — scaffold.sh 와 같다).
if ($PSBoundParameters.ContainsKey('DbPassword') -and $DbPassword) {
  Write-Warn2 "-DbPassword 인자는 프로세스 목록·셸 기록에 남습니다 — 환경변수 SCAFFOLD_DB_PASSWORD 를 쓰세요."
} elseif ($env:SCAFFOLD_DB_PASSWORD) {
  $DbPassword = $env:SCAFFOLD_DB_PASSWORD
}
if (-not $Name)   { $Name = Read-HostSafe "프로젝트 이름 (예: project_test)" }
if (-not $Name)   { Stop-Scaffold "프로젝트 이름이 필요합니다." }
# ⛔ 이름은 Python 문자열 리터럴(app\main.py)·HTML 제목과 기본 생성 위치(부모\<이름>)에 그대로 들어간다.
#    " \ ../ 같은 문자는 코드를 깨거나 경로를 벗어나므로 허용 목록으로만 받는다 (scaffold.sh 와 같은 규칙).
if ($Name -cnotmatch '^[A-Za-z0-9](?:[A-Za-z0-9 _-]{0,62}[A-Za-z0-9_-])?\z') {
  Write-Host "  [X]  사용할 수 없는 프로젝트 이름입니다: $Name" -ForegroundColor Red
  Write-Host "        ASCII 영문자·숫자로 시작하고 영문자·숫자·공백·'_'·'-' 만 쓸 수 있습니다(최대 64자, 공백으로 끝나면 안 됨)." -ForegroundColor Yellow
  exit 1
}
$snake = ($Name -creplace '([a-z0-9])([A-Z])', '$1_$2') -replace '[^A-Za-z0-9]+', '_'
$snake = $snake.Trim('_').ToLower()
# ⛔ 식별자가 비면 DATABASE_URL 에 DB 이름이 없고 쿠키 이름이 "_session" 이 된다.
#    위 허용 목록이 영숫자 시작을 강제하므로 정상 경로에서는 오지 않지만, 방어로 남긴다.
if (-not $snake) {
  Write-Warn2 "프로젝트 이름에서 식별자를 만들 수 없습니다: $Name"
  Write-Host "        ASCII 영문자·숫자를 1자 이상 포함하세요 (DB 이름·쿠키 이름에 쓰입니다)." -ForegroundColor Yellow
  exit 1
}
if (-not $DbName) { $DbName = $snake }

# -Target 미지정 시 기본값: 템플릿 저장소의 부모 폴더에 <이름> 으로 생성
if (-not $Target) {
  $defaultTarget = Join-Path (Split-Path $TemplateDir -Parent) $Name
  $i = Read-HostSafe "생성 위치 [$defaultTarget]"
  $Target = if ($i) { $i } else { $defaultTarget }
}
# 상대 경로는 .NET 프로세스 디렉토리가 아니라 현재 PowerShell 위치 기준으로 해석한다.
# (PS 5.1 호환: 2-인자 GetFullPath 오버로드가 없으므로 직접 결합 후 정규화)
if (-not [System.IO.Path]::IsPathRooted($Target)) {
  $Target = Join-Path (Get-Location).Path $Target
}
# 링크를 푼 실제 경로로 바꾼다 — 이후 복사·치환·안내가 모두 이 경로를 쓴다(scaffold.sh 의 물리 경로와 같다).
$Target = Resolve-RealPath $Target
$_TemplateReal = Resolve-RealPath $TemplateDir

# ⛔ 대상이 템플릿 저장소 자신·그 하위면 골격·문서가 덮이거나 토큰이 치환돼 템플릿이 망가진다.
#    대상이 템플릿의 상위면 토큰 치환이 템플릿 저장소까지 훑는다. 어느 경우든 무조건 중단한다.
#    두 쪽 모두 링크를 푼 실제 경로로 비교한다(정션·심볼릭 링크로 우회하지 못하게).
if (Test-PathWithin $Target $_TemplateReal) {
  Stop-Scaffold "생성 위치가 템플릿 저장소 안입니다 — 템플릿 밖의 경로를 지정하세요: $Target"
}
if (Test-PathWithin $_TemplateReal $Target) {
  Stop-Scaffold "생성 위치가 템플릿 저장소를 포함합니다 — 템플릿 밖의 별도 폴더를 지정하세요: $Target"
}
if (Test-Path -LiteralPath $Target -PathType Leaf) {
  Stop-Scaffold "생성 위치가 이미 파일로 존재합니다: $Target"
}
# ⛔ 비어 있지 않은 폴더 위 재실행은 파괴적이다(사용자가 고친 골격 파일이 원본으로 되돌아간다).
#    대화형이면 확인을 받고, 비대화형(CI·스크립트)이면 중단한다 (scaffold.sh 와 동일).
if ((Test-Path -LiteralPath $Target -PathType Container) -and
    (Get-ChildItem -LiteralPath $Target -Force -ErrorAction SilentlyContinue | Select-Object -First 1)) {
  Write-Warn2 "대상 디렉토리가 비어있지 않습니다: $Target"
  if (Test-Interactive) {
    $_ans = Read-HostSafe "  계속할까요? 기존 파일 위에 골격을 덮어씁니다 (y/N)"
    if ($_ans -notmatch '^[Yy]') { Write-Host "중단합니다."; exit 1 }
  } else {
    Stop-Scaffold "비대화형 실행이므로 중단합니다. 덮어쓰려면 대상 디렉터리를 비우거나 대화형으로 실행하세요."
  }
}
Write-Ok "이름=$Name  snake=$snake  위치=$Target"

# ---------- 2. 런타임 확인 (미달이면 bootstrap.ps1 자동 실행) ----------
# 런타임 핀 로드 — ⚠️ 반드시 Enable-VersionManagers 보다 먼저 읽어야 한다.
# pyenv 는 "shim 이 PATH 에 있다"와 "어떤 버전을 쓴다"가 별개라, 활성화 시점에 핀 값이 필요하다.
$_pyPinFile   = Join-Path $SkeletonDir '.python-version'
$_pyPin       = if (Test-Path -LiteralPath $_pyPinFile) { "$(Get-Content -LiteralPath $_pyPinFile -TotalCount 1)".Trim() } else { "" }

# pyenv-win 활성화 (설치돼 있으면 현재 세션에 적용)
function Enable-VersionManagers {
  $pyenvRoot = "$env:USERPROFILE\.pyenv\pyenv-win"
  if (Test-Path -LiteralPath $pyenvRoot) {
    $env:PYENV      = $pyenvRoot
    $env:PYENV_ROOT = $pyenvRoot
    $env:PYENV_HOME = $pyenvRoot
    # PATH 선두에 추가 — 기존 항목은 위치(끝 항목 포함)와 무관하게 제거해 재실행 시 중복 누적 방지
    $rest = ($env:Path -split ';' | Where-Object { $_ -and $_ -ne "$pyenvRoot\bin" -and $_ -ne "$pyenvRoot\shims" }) -join ';'
    $env:Path = "$pyenvRoot\bin;$pyenvRoot\shims;" + $rest
    # ⛔ PATH 에 shim 을 올리는 것과 "어떤 버전을 쓸지" 는 별개다. pyenv global 이 없거나 핀보다 낮으면
    #    shim 이 실패하거나 옛 버전을 가리켜, bootstrap 이 핀을 설치·재사용한 뒤에도 검증 단계에서 실패한다.
    #    ⚠️ 설치돼 있지 않은 버전을 지정하면 모든 shim 호출이 깨지므로 반드시 설치 여부를 확인한다.
    $_installedNow = @($(try { pyenv versions --bare 2>&1 | Out-String } catch { "" }) -split '\r?\n' |
      ForEach-Object { $_.Trim() } | Where-Object { $_ })
    if ($_pyPin -and ($_installedNow -contains $_pyPin)) {
      $env:PYENV_VERSION = $_pyPin
    } else {
      # 핀이 설치돼 있지 않으면 하한을 충족하는 설치본 중 가장 높은 것을 고른다 (옛 전역 버전 폴백 방지)
      $_minPy = if ($_min['MIN_PYTHON']) { $_min['MIN_PYTHON'] } else { '3.13' }
      $_cand = $_installedNow | Where-Object { $_ -match '^\d+\.\d+\.\d+$' -and $_.StartsWith("$_minPy.") } |
        Sort-Object { [version]$_ } | Select-Object -Last 1
      if ($_cand) { $env:PYENV_VERSION = $_cand }
    }
  }
}
Enable-VersionManagers

function _Get-SemVer([string]$raw) {
  if ($raw -and ($raw -match '(\d+)\.(\d+)')) { return @{ Major=[int]$matches[1]; Minor=[int]$matches[2] } }
  return $null
}
function _Meets($have, [string]$minStr) {
  if (-not $have) { return $false }
  $mm = $minStr.Split('.'); $mj = [int]$mm[0]; $mn = if ($mm.Count -gt 1) { [int]$mm[1] } else { 0 }
  return ($have.Major -gt $mj -or ($have.Major -eq $mj -and $have.Minor -ge $mn))
}

# bootstrap 이 필요한 기준은 "런타임이 하한 미달"이다 (versions.env 정책: 이상이면 재사용).
# ⛔ pyenv 가 없다는 이유만으로 bootstrap 을 강제하지 않는다 — Windows 에서 pyenv-win 은
# 자동 설치 대상이 아니라, 이미 조건을 만족한 환경까지 골격 생성 전에 막아버린다.
$_needBootstrap = $false
$_bootstrapReason = ""
$_pyVer = _Get-SemVer $(try { python --version 2>&1 | Out-String } catch { "" })
# PS 5.1 호환: '??'(null 병합, PS7+) 대신 if 식 사용. 폴백은 versions.env 와 동일한 3.13.
$_minPython = if ($_min['MIN_PYTHON']) { $_min['MIN_PYTHON'] } else { '3.13' }
if (-not (_Meets $_pyVer $_minPython)) { $_needBootstrap = $true; $_bootstrapReason = "Python 하한($_minPython) 미달" }
# skeleton\.python-version 핀 처리
#  - pyenv 가 있으면: 핀된 정확한 버전이 실제 설치돼 있어야 한다(없으면 bootstrap 이 설치).
#  - pyenv 가 없으면: 핀을 강제할 수단이 없다. 하한을 충족하는 Python 을 그대로 쓰되,
#    CI 는 .python-version 을 읽으므로 버전이 다르면 경고만 남긴다.
if ($_pyPin) {
  if (Get-Command pyenv -ErrorAction SilentlyContinue) {
    if (-not $_needBootstrap) {
      $_pyenvInstalled = $(try { pyenv versions --bare 2>&1 | Out-String } catch { "" })
      $_installedList = "$_pyenvInstalled" -split '\r?\n' | ForEach-Object { $_.Trim() }
      if ($_installedList -notcontains $_pyPin) { $_needBootstrap = $true; $_bootstrapReason = "pyenv 에 Python 핀($_pyPin) 미설치" }
    }
  } elseif (-not $_needBootstrap) {
    $_pyActual = ($(try { python --version 2>&1 | Out-String } catch { "" }) -replace '[^0-9.]', '').Trim()
    if ($_pyActual -and $_pyActual -ne $_pyPin -and -not $_pyActual.StartsWith("$_pyPin.")) {
      Write-Warn2 "Python 핀($_pyPin)과 설치본($_pyActual)이 다릅니다 — CI 는 .python-version 을 읽으므로 로컬과 다른 버전을 씁니다."
      Write-Host "        일치시키려면 pyenv-win 을 설치해 핀 버전을 쓰거나, 생성 후 프로젝트의 .python-version 을 설치본에 맞추세요." -ForegroundColor Yellow
    }
  }
}

if ($_needBootstrap) {
  if (-not (Test-Path -LiteralPath $_Bootstrap)) {
    Stop-Scaffold "bootstrap.ps1 을 찾을 수 없습니다 ($_Bootstrap). 수동으로 먼저 실행하세요."
  }
  Write-Warn2 "$_bootstrapReason — bootstrap.ps1 을 먼저 실행합니다 …"
  # ⛔ -ProjectRoot 없이 실행하면 bootstrap 이 핀 파일이 없을 때 템플릿의 skeleton\ 에 핀을 기록해
  #    리포를 오염시킬 수 있다. 템플릿 오염 방지용 임시 폴더를 넘기고, 끝나면 지운다.
  #    골격의 핀을 미리 심어 bootstrap 이 "기존 핀 존중" 경로를 타게 한다 — 빈 폴더면 bootstrap 이
  #    임의의 최신 패치를 골라 설치해, 생성 프로젝트의 핀(골격 값)과 다른 버전이 깔린다.
  #    bootstrap 은 핀이 이미 있으면 기록하지 않으므로, 생성 프로젝트의 핀은 언제나 골격 값이다.
  $_PinDir = Join-Path ([System.IO.Path]::GetTempPath()) ("scaffold-pin-" + [guid]::NewGuid().ToString("N").Substring(0,8))
  [void][System.IO.Directory]::CreateDirectory($_PinDir)
  if (Test-Path -LiteralPath $_pyPinFile) { Copy-Item -LiteralPath $_pyPinFile -Destination (Join-Path $_PinDir '.python-version') -Force }
  # PS 5.1 은 스크립트/네이티브 명령 실패를 자동 예외화하지 않고, in-process 호출의
  # $LASTEXITCODE 는 내부 마지막 네이티브 명령의 잔존값이라 신뢰할 수 없다.
  # → 예외 포착 + bootstrap 결과(실제 런타임 버전) 검증으로 실패를 감지한다 (scaffold.sh 와 동일하게 실패 시 중단).
  # 검증 기준은 "런타임이 하한을 충족하는가"이지 "pyenv 가 설치됐는가"가 아니다 —
  # 관리자 없이 기존 설치본을 재사용하는 경로가 정상 경로이기 때문이다.
  $_bootstrapOk = $true
  $_runtimeOk = $true
  try { & $_Bootstrap -ProjectRoot $_PinDir -SkipNextSteps } catch {
    Write-Warn2 "bootstrap.ps1 실행 중 오류: $($_.Exception.Message)"
    $_bootstrapOk = $false
  } finally {
    Remove-Item -LiteralPath $_PinDir -Recurse -Force -ErrorAction SilentlyContinue
  }
  # ⛔ 활성화 실패를 곧바로 중단 사유로 삼지 않는다 — 관리자 없이 기존 설치본을 재사용하는
  #    정상 경로까지 막아버린다(scaffold.sh 와 동일). 판정은 아래 런타임 재검증이 한다.
  Enable-VersionManagers
  $_pyAfter = _Get-SemVer $(try { python --version 2>&1 | Out-String } catch { "" })
  if ($_bootstrapOk -and -not (_Meets $_pyAfter $_minPython)) { $_runtimeOk = $false }
  # 핀이 pyenv 에 설치됐는지는 경고 대상이지 중단 사유가 아니다.
  # bootstrap 이 핀을 설치하지 못해도 하한을 충족하는 Python 으로 폴백했을 수 있고, 그 경우
  # 위의 런타임 검증을 이미 통과했다. 여기서 중단하면 폴백 경로가 의미를 잃는다.
  if ($_bootstrapOk -and $_runtimeOk -and $_pyPin -and (Get-Command pyenv -ErrorAction SilentlyContinue)) {
    $_installed2 = $(try { pyenv versions --bare 2>&1 | Out-String } catch { "" })
    $_installedList2 = "$_installed2" -split '\r?\n' | ForEach-Object { $_.Trim() }
    if ($_installedList2 -notcontains $_pyPin) {
      Write-Warn2 "Python 핀 $_pyPin 이 pyenv 에 없습니다 — 하한을 충족하는 설치본으로 진행합니다. CI 는 핀을 사용합니다."
    }
  }
  # 실패 문구는 scaffold.sh 와 같은 두 갈래다.
  if (-not $_bootstrapOk) {
    Stop-Scaffold "bootstrap 실패 — 스캐폴드를 중단합니다. 위 로그의 오류를 해결한 뒤 다시 실행하세요."
  }
  if (-not $_runtimeOk) {
    Stop-Scaffold "bootstrap 후에도 Python $_minPython 이상을 찾지 못했습니다 — 스캐폴드를 중단합니다."
  }
}

# ---------- 3. DB 접속 정보 ----------
# DB 접속 값 검사 — 값은 psql 인자·SQL 식별자·.env 의 DATABASE_URL 에 들어간다. 규칙은 scaffold.sh 의 _check_db_values 와 같다.
#  - 이름: 영문자·숫자·'_' 1~63자(PostgreSQL 식별자 한도 — 넘으면 서버가 조용히 잘라 URL 과 어긋난다)
#  - 호스트: URL 에 인코딩 없이 들어가므로 허용 목록 — 호스트 이름·IPv4(영문자·숫자·'.'·'-'·'_') 또는 [IPv6]
#  - 사용자: 제어 문자·큰따옴표 금지(URL 에는 인코딩해 넣는다), 포트: 1~65535
#  - 비밀번호: URL 에는 인코딩해 넣으므로(%0A 등) 제한하지 않는다. ⛔ 그래서 .env 에 줄바꿈이 들어갈 수 없다.
function Assert-DbValues {
  if ($DbName -cnotmatch '^[A-Za-z0-9_]{1,63}\z') {
    Stop-Scaffold "DB 이름은 영문자·숫자·'_' 1~63자만 쓸 수 있습니다: $DbName"
  }
  if ($DbHost -cnotmatch '^(?:[A-Za-z0-9._-]{1,253}|\[[0-9A-Fa-f:.]{2,45}\])\z') {
    Stop-Scaffold "DB 호스트는 호스트 이름·IPv4(영문자·숫자·'.'·'-'·'_') 또는 [IPv6] 만 쓸 수 있습니다: $DbHost"
  }
  if (-not $DbUser -or $DbUser.Length -gt 63 -or $DbUser -match '[\p{Cc}"]') {
    Stop-Scaffold "DB 사용자는 1~63자이고 제어 문자·큰따옴표(`")를 쓸 수 없습니다."
  }
  if ($DbPort -lt 1 -or $DbPort -gt 65535) {
    Stop-Scaffold "DB 포트는 1~65535 여야 합니다: $DbPort"
  }
}
if (-not $SkipDb) {
  Write-Step "PostgreSQL 접속 정보 (psql 로 DB 생성)"
  $i = Read-HostSafe "DB host [$DbHost]"; if ($i) { $DbHost = $i }
  $i = Read-HostSafe "DB port [$DbPort]"
  if ($i) {
    $_port = 0
    if ([int]::TryParse($i, [ref]$_port)) { $DbPort = $_port }
    else { Write-Warn2 "포트가 숫자가 아닙니다: '$i' — 기존 값 $DbPort 유지" }
  }
  $i = Read-HostSafe "DB user [$DbUser]"; if ($i) { $DbUser = $i }
  if (-not $DbPassword) {
    # 비밀번호는 화면에 표시하지 않는다 (scaffold.sh 의 read -s 대응)
    try {
      $_sec  = Read-Host "DB password" -AsSecureString
      $_bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($_sec)
      try     { $DbPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($_bstr) }
      finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($_bstr) }
    } catch { $DbPassword = "" }
  }
  $i = Read-HostSafe "DB name [$DbName]"; if ($i) { $DbName = $i }
}
# -SkipDb 여도 값은 .env 의 DATABASE_URL 에 들어가므로 항상 검사한다.
Assert-DbValues

# DB 사전 접속 검사 (psql 로 SELECT 1) — 접속 정보 입력 직후 1회 가볍게 확인한다.
# 실패하면 접속 실패 요지를 경고하고, 대화형이면 1회 재입력, 비대화형이면 DB 단계 전체를 건너뛴다.
# $DbUnreachable = $true 이면 아래 DB 단계에서 CREATE DATABASE·alembic 을 모두 생략한다.
# psql 이 없으면 검사 불가 → 아래 DB 단계에서 'psql 없음' 으로 안내한다.
$DbUnreachable = $false
if (-not $SkipDb) {
  Enable-Psql   # PATH 에 없으면 표준 설치 경로를 찾아 세션 PATH 에 추가
  $_psqlPre = Get-Command psql -ErrorAction SilentlyContinue
  if ($_psqlPre) {
    $_dbRetried = $false
    while ($true) {
      $env:PGPASSWORD = $DbPassword
      $_pcRc = 1; $_pcErr = ""
      try {
        # 성공/실패 출력을 모두 캡처(2>&1). PS 5.1 은 EAP=Stop + 네이티브 stderr 조합에서 예외화될 수 있어 감싼다.
        $_pcOut = & psql -w -h $DbHost -p $DbPort -U $DbUser -d postgres -tAc "SELECT 1" 2>&1
        $_pcRc  = $LASTEXITCODE
        $_pcErr = ($_pcOut | Out-String)
      } catch {
        $_pcErr = $_.Exception.Message
        $_pcRc  = 1
      } finally {
        Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
      }
      if ($_pcRc -eq 0) { break }
      $_pcSummary = ("$_pcErr" -split "\r?\n" | Where-Object { $_.Trim() -ne "" } | Select-Object -Last 1)
      Write-Warn2 "접속 실패: $(if ($_pcSummary) { $_pcSummary } else { 'psql 연결에 실패했습니다' })"
      if ((Test-Interactive) -and -not $_dbRetried) {
        $_dbRetried = $true
        Write-Warn2 "접속정보를 다시 입력하세요 (1회 재시도, Enter 는 기존값 유지)"
        $i = Read-HostSafe "DB host [$DbHost]"; if ($i) { $DbHost = $i }
        $i = Read-HostSafe "DB port [$DbPort]"
        if ($i) {
          $_p = 0
          if ([int]::TryParse($i, [ref]$_p)) { $DbPort = $_p }
          else { Write-Warn2 "포트가 숫자가 아닙니다: '$i' — 기존 값 $DbPort 유지" }
        }
        $i = Read-HostSafe "DB user [$DbUser]"; if ($i) { $DbUser = $i }
        try {
          $_sec  = Read-Host "DB password [기존값 유지]" -AsSecureString
          $_bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($_sec)
          try     { $_pw = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($_bstr) }
          finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($_bstr) }
          if ($_pw) { $DbPassword = $_pw }
        } catch {}
        $i = Read-HostSafe "DB name [$DbName]"; if ($i) { $DbName = $i }
        Assert-DbValues
        continue
      }
      Write-Warn2 "DB 접속 불가로 판단 — DB 생성/마이그레이션 단계를 건너뜁니다"
      $DbUnreachable = $true
      break
    }
  }
}

# 사용자·비밀번호는 URL 인코딩해 DATABASE_URL 에 넣는다 (@ : / # ? % 줄바꿈 등 특수문자 안전).
# 호스트·이름은 위 Assert-DbValues 의 허용 목록을 통과한 값이라 인코딩이 필요 없다.
$databaseUrl = "postgresql+psycopg2://$([uri]::EscapeDataString("$DbUser")):$([uri]::EscapeDataString("$DbPassword"))@${DbHost}:${DbPort}/${DbName}"
# ⛔ 방어 이중화 — 제어 문자(줄바꿈 등)가 남아 있으면 .env 에 다른 키를 끼워 넣을 수 있다. 쓰기 전에 중단한다.
if ($databaseUrl -match '\p{Cc}') { Stop-Scaffold "DATABASE_URL 에 제어 문자가 있습니다 — 중단합니다." }
# SECRET_KEY 는 Flask 서명 쿠키(flash·CSRF 토큰)의 서명키이므로 암호학적 난수 사용 (scaffold.sh 의 openssl rand 대응).
# 32 bytes(64 hex) — 앱의 운영 하한(32 bytes)을 넉넉히 넘는다.
$_rngBytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($_rngBytes)
$secret = ([System.BitConverter]::ToString($_rngBytes) -replace '-', '').ToLower()
# 초기 관리자 비밀번호도 무작위로 생성한다.
# ⛔ 하드코딩된 기본값(admin123)을 쓰면 이 템플릿으로 만든 모든 프로젝트가 같은 자격증명을 갖는다.
$_pwBytes = New-Object byte[] 12
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($_pwBytes)
$seedAdminPw = [Convert]::ToBase64String($_pwBytes) -replace '[/+=]', ''

# ---------- 4. 골격 복사 ----------
Write-Step "골격 복사 → $Target"
[void][System.IO.Directory]::CreateDirectory($Target)
# 닷파일(.gitignore·.python-version·.github·.claude 등) 포함 전체 복사.
# ⛔ Copy-Item 통째 복사는 쓰지 않는다 — 템플릿 저장소에서 개발/검증을 하면 skeleton\ 안에
#    .venv·.tools(Tailwind CLI 실행 파일, 100MB 이상)·업로드 같은 gitignore 산출물이 남는데,
#    그대로 복사되면 생성 프로젝트가 부풀고 토큰 치환이 산출물을 붙잡는다. 실제 .env 가 복사되면
#    템플릿의 SECRET_KEY 가 새는 보안 문제도 된다 (scaffold.sh 의 tar --exclude 와 동일 결과).
#    robocopy 는 Windows 기본 탑재이고 /XD·/XF 로 디렉터리·파일을 원천 제외한다.
#    /XJ 는 골격 안의 정션·심볼릭 링크를 따라가지 않는다 — 링크가 가리키는 골격 밖 내용이 복사되지 않는다
#    (scaffold.sh 의 tar 도 링크를 따라가지 않는다. 골격에는 링크가 없다).
robocopy $SkeletonDir $Target /E /XJ /XD $CopyExcludeDirs /XF $CopyExcludeFiles /NFL /NDL /NJH /NJS /NP | Out-Null
# robocopy 종료 코드: 0~7 = 성공(복사 결과 비트마스크), 8 이상 = 실패
if ($LASTEXITCODE -ge 8) { Stop-Scaffold "골격 복사 실패 (robocopy 코드 $LASTEXITCODE) — 중단합니다" }
# ⛔ 성공 시에도 robocopy 는 1(복사함)을 남긴다. 지우지 않으면 스크립트 종료 코드로 새어 나가
#    성공한 실행이 실패(1)로 보인다.
$global:LASTEXITCODE = 0
Write-Ok "복사 완료"

# 생성 기준 기록 — 템플릿의 이후 수정은 생성 프로젝트에 자동으로 반영되지 않는다. 어떤 수정을 옮길지
# flask-starter CHANGELOG 와 비교하는 기준으로 커밋을 남긴다(git 이 없거나 zip 으로 받았으면 unknown,
# 커밋하지 않은 변경이 있으면 -dirty). 내용은 scaffold.sh 와 같다(LF, BOM 없음).
$_starterRev = 'unknown'
if (Get-Command git -ErrorAction SilentlyContinue) {
  # PS 5.1 은 EAP=Stop + 네이티브 stderr(저장소가 아니면 git 이 fatal 을 쓴다) 조합에서 예외화될 수 있어 감싼다.
  $_eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  try {
    $_rev = "$(& git -C $TemplateDir rev-parse --short=7 HEAD 2>$null)".Trim()
    if ($LASTEXITCODE -eq 0 -and $_rev) {
      $_starterRev = $_rev
      & git -C $TemplateDir diff --quiet HEAD -- 2>$null
      if ($LASTEXITCODE -ne 0) { $_starterRev = "$_starterRev-dirty" }
    }
  } catch { $_starterRev = 'unknown' } finally { $ErrorActionPreference = $_eap; $global:LASTEXITCODE = 0 }
}
$_starterNote = "# 이 프로젝트를 생성한 flask-starter 커밋 — 템플릿의 이후 수정은 자동으로 반영되지 않는다.`n" +
  "# 옮길 변경은 flask-starter 의 CHANGELOG.md 에서 이 커밋 이후 항목을 보고 고른다(README 「템플릿 수정 반영」).`n" +
  "commit=$_starterRev`n"
[System.IO.File]::WriteAllText((Join-Path $Target '.flask-starter'), $_starterNote, (New-Object System.Text.UTF8Encoding($false)))
Write-Ok "생성 기준 기록: .flask-starter (commit=$_starterRev)"

# ---------- 5. 토큰 치환 ----------
Write-Step "토큰 치환"
# 복사 단계가 산출물을 제외하지만, 기존 디렉토리 위에 덮어쓴 재실행(이미 install/build 된
# 프로젝트)에서는 .venv·.tools 가 남아 있다 — 디렉터리 이름으로 가지치기해 산출물을
# 문자열 치환이 붙잡지 않게 한다(방어 이중화, scaffold.sh 의 os.walk 가지치기와 동일).
# 대상 아래만 걸으므로 대상 경로 자체(예: C:\build\MyApp)에 같은 이름이 있어도 오탐하지 않는다.
# ⛔ Get-ChildItem -Path 는 [ ] 를 와일드카드로 해석해 대상 경로에 [ ] 가 있으면 조용히 0건이 된다
#    (= 토큰이 그대로 남는다). .NET 열거로 리터럴 경로를 걷는다.
# 바이트 단위 치환(토큰은 ASCII): Latin-1 은 바이트↔문자가 1:1 이라 원본의 BOM·줄바꿈·인코딩이
# 그대로 보존된다 — scaffold.sh 의 python 바이트 치환과 같은 결과.
$_latin1 = [System.Text.Encoding]::GetEncoding(28591)
$_tokens = @(
  @('__PROJECT_NAME__',  $_latin1.GetString($Enc.GetBytes($Name))),
  @('__PROJECT_SNAKE__', $_latin1.GetString($Enc.GetBytes($snake)))
)
$_stack = [System.Collections.Generic.Stack[System.IO.DirectoryInfo]]::new()
$_stack.Push([System.IO.DirectoryInfo]::new($Target))
while ($_stack.Count -gt 0) {
  $_dir = $_stack.Pop()
  foreach ($_sub in $_dir.GetDirectories()) {
    # ⛔ 링크(정션·심볼릭 링크) 폴더는 따라가지 않는다 — 대상 밖의 파일을 치환하게 된다(scaffold.sh 의 os.walk 와 같다).
    if ($_sub.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { continue }
    if ($PruneDirs -cnotcontains $_sub.Name) { $_stack.Push($_sub) }
  }
  foreach ($_f in $_dir.GetFiles()) {
    # 링크 파일도 건너뛴다 — 쓰기가 링크 너머의 원본 파일에 닿는다(scaffold.sh 와 같다).
    if ($_f.Attributes -band [System.IO.FileAttributes]::ReparsePoint) { continue }
    if ($TokenExtensions -cnotcontains $_f.Extension) { continue }
    $_orig = $_latin1.GetString([System.IO.File]::ReadAllBytes($_f.FullName))
    $_new = $_orig
    foreach ($_t in $_tokens) { $_new = $_new.Replace($_t[0], $_t[1]) }
    # 변경된 파일만 재기록 (재실행 시 불필요한 mtime 변경 방지 — scaffold.sh 와 동일)
    if (-not [string]::Equals($_new, $_orig, [StringComparison]::Ordinal)) {
      [System.IO.File]::WriteAllBytes($_f.FullName, $_latin1.GetBytes($_new))
    }
  }
}
Write-Ok "치환 완료"

# ---------- 6. .env 생성 ----------
Write-Step ".env 생성 (OS 무관 주입 — ARCHITECTURE.md §5)"
# 키 집합은 .env.example 과 같아야 한다(설명은 그 파일 참고, scaffold.sh 와 동일).
$envContent = @"
DATABASE_URL=$databaseUrl
APP_ENV=development
LOG_LEVEL=INFO
SECRET_KEY=$secret
# 로그인 세션·시도 제한 (ARCHITECTURE.md §9) — 코드 기본값과 같지만, 운영자가 .env 만 보고도
# 조절 지점을 알 수 있도록 명시한다.
REFRESH_TOKEN_EXPIRE_DAYS=14
LOGIN_MAX_FAILURES=5
LOGIN_LOCKOUT_MINUTES=15
# 운영(HTTPS)에서는 true 로 바꾼다 (APP_ENV=production + false 면 기동 거부).
COOKIE_SECURE=false
# HTTPS 를 끝내는 리버스 프록시(nginx) 뒤에서 운영하면 1 로 바꾼다(앱을 바로 노출하면 0).
TRUSTED_PROXY_HOPS=0
# 업로드 저장소·크기 상한 — 값은 .env.example 과 같다(설명은 그 파일 참고).
UPLOAD_DIR=uploads
PUBLIC_FILES_BASE_URL=
MAX_IMAGE_UPLOAD_MB=5
MAX_ATTACHMENT_UPLOAD_MB=20
TZ=Asia/Seoul
# 초기 관리자 시드 — 코드 기본값은 꺼져 있고(app/config.py) 개발 편의를 위해 여기서만 켠다.
# ⛔ 배포 전 SEED_DEFAULT_ADMIN=false 로 끄고 APP_ENV=production 으로 바꾼다.
SEED_DEFAULT_ADMIN=true
DEFAULT_ADMIN_PASSWORD=$seedAdminPw

"@
# 줄바꿈 LF 통일, 끝 줄바꿈 1개 (scaffold.sh 의 heredoc 결과와 동일)
$envContent = ($envContent -replace "`r`n", "`n").TrimEnd("`n") + "`n"
# ⛔ .env 는 DB 비밀번호와 서명키를 담는다. 상속 ACL 을 끊고 현재 사용자에게만 허용한다
#    (scaffold.sh 의 umask 077·chmod 600 대응).
$_envPath = Join-Path $Target '.env'
# ⛔ 기존 .env 를 덮어쓰면 SECRET_KEY 가 재발급되어 flash·CSRF 쿠키가 전부 무효가 된다. 백업을 남긴다.
#    복사(Copy-Item)하면 백업이 폴더의 상속 ACL 을 받아 다른 사용자도 읽게 되므로, 이름만 바꿔(Move)
#    원본의 보안 설정을 유지한 뒤 백업에도 같은 제한 ACL 을 다시 건다.
if (Test-Path -LiteralPath $_envPath) {
  $_envBak = "$_envPath.bak." + (Get-Date -Format 'yyyyMMddHHmmss')
  [System.IO.File]::Move($_envPath, $_envBak)
  try { Set-OwnerOnlyAcl $_envBak } catch {
    Write-Warn2 "백업 파일 권한 제한 실패 — 직접 제한하거나 삭제하세요: $_envBak ($($_.Exception.Message))"
    Add-Incomplete ".env 백업 권한 제한"
  }
  Write-Warn2 "기존 .env 를 백업했습니다: $(Split-Path $_envBak -Leaf)"
}
# 빈 파일을 먼저 만들고 권한을 제한한 뒤 내용을 쓴다 — 비밀이 상속 ACL 상태로 디스크에 놓이는 순간이 없다.
# ⛔ 권한 제한에 실패하면 비밀을 쓰지 않고 중단한다 — 상속 ACL 그대로 쓰면 다른 사용자도 읽는다
#    (scaffold.sh 는 umask 077 로 처음부터 소유자 전용 파일을 만들고, 만들지 못하면 중단한다).
[System.IO.File]::WriteAllText($_envPath, "", $Enc)
try { Set-OwnerOnlyAcl $_envPath } catch {
  $_aclErr = $_.Exception.Message
  Remove-Item -LiteralPath $_envPath -Force -ErrorAction SilentlyContinue
  Stop-Scaffold ".env 권한 제한 실패 — 비밀값을 쓰지 않고 중단합니다 ($_aclErr). 폴더 권한을 확인한 뒤 다시 실행하세요."
}
[System.IO.File]::WriteAllText($_envPath, $envContent, $Enc)
Write-Ok ".env 생성 (DATABASE_URL, SECRET_KEY 주입)"

$venvPy = Join-Path $Target '.venv\Scripts\python.exe'

# ---------- 7. Python 의존성 설치 ----------
if (-not $SkipInstall) {
  Write-Step "venv + 의존성 설치"
  if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    # bash 와 동일하게 warn 후 계속 (다음 단계에서 venv 부재를 다시 안내)
    Write-Warn2 "python 없음 — 의존성 설치 건너뜀"
    Add-Incomplete "venv·의존성 설치 (python 없음)"
  } else {
    Push-Location -LiteralPath $Target
    try {
      python -m venv .venv
      if (-not (Test-Path -LiteralPath $venvPy)) {
        Write-Warn2 "venv 생성 실패 — 'python -m venv .venv' 로 직접 확인하세요"
        Add-Incomplete "venv 생성"
      } else {
        # ⛔ pip 자체를 --upgrade 로 올리지 않는다(고정되지 않은 최신 pip 를 받는다). venv 에 딸린 pip 로
        #    전이 의존성까지 해시로 고정한 requirements.lock 을 설치한다 — 해시가 다른 파일은 설치하지 않는다(scaffold.sh 와 같다).
        & $venvPy -m pip install --require-hashes -r requirements.lock
        if ($LASTEXITCODE -ne 0) {
          Write-Warn2 "pip install 미완료 — '.\.venv\Scripts\python -m pip install --require-hashes -r requirements.lock'"
          Add-Incomplete "의존성 설치 (pip install)"
        } else { Write-Ok "의존성 설치 완료" }
      }
    } finally { Pop-Location }
  }
} else { Write-Warn2 "SkipInstall: 의존성 설치 건너뜀" }

# ---------- 8. DB 생성 + 테이블(Alembic) ----------
# DB 수동 실행 안내(한 블록만) — CREATE DATABASE·alembic 을 모두 건너뛸 때 보여준다(scaffold.sh 와 같은 형식).
# 명령 인자 대신 "접속 후 실행할 SQL" 로 보여준다 — 셸마다 다른 따옴표 규칙 때문에 이름에 대문자·'-' 가 있으면
# -c 인자 한 줄로는 두 셸 모두에서 맞게 쓸 수 없다. 이름은 항상 큰따옴표 식별자로 인용한다.
function Show-DbManualGuide([string]$Reason, [string]$Incomplete) {
  Write-Warn2 "$Reason — 다음을 수동 실행:"
  Write-Host "        1) DB 생성·시각대: psql -h $DbHost -p $DbPort -U $DbUser -d postgres 로 접속해 실행" -ForegroundColor White
  Write-Host "             CREATE DATABASE `"$DbName`";" -ForegroundColor White
  Write-Host "             ALTER DATABASE `"$DbName`" SET timezone TO 'Asia/Seoul';" -ForegroundColor White
  Write-Host "        2) 테이블 생성:    .\.venv\Scripts\python -m alembic upgrade head" -ForegroundColor White
  Add-Incomplete $Incomplete
}
function Show-DbUnreachableGuide {
  Show-DbManualGuide "DB 접속 불가(접속정보 host/port/user/password 확인)" "DB 생성·마이그레이션 (접속 불가)"
}
# SQL 을 표준입력으로 psql 에 넘긴다 (PGPASSWORD 는 호출 동안만 설정).
# DB 이름은 -v dbname=… 변수로 넘기고 SQL 안에서 :"dbname"(식별자)·:'dbname'(문자열)로 인용한다 —
# ⛔ "…`"이름`"…" 처럼 큰따옴표를 인자에 넣으면 PowerShell 버전마다 네이티브 인자 인용 규칙이 달라
#    따옴표가 사라지거나 이중 이스케이프된다. 표준입력 SQL 은 ASCII 뿐이라 인코딩 문제도 없다.
function Invoke-PsqlScript([string]$sql, [switch]$Tuples) {
  $env:PGPASSWORD = $DbPassword
  $psqlArgs = @('-w', '-X', '-q', '-v', 'ON_ERROR_STOP=1', '-v', "dbname=$DbName",
                '-h', $DbHost, '-p', "$DbPort", '-U', $DbUser, '-d', 'postgres')
  if ($Tuples) { $psqlArgs += '-tA' }
  try {
    $out = $sql | & psql @psqlArgs
    return [pscustomobject]@{ Ok = ($LASTEXITCODE -eq 0); Out = "$out".Trim() }
  } catch {
    Write-Warn2 "psql 실행 오류: $($_.Exception.Message)"
    return [pscustomobject]@{ Ok = $false; Out = "" }
  } finally { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
}
# alembic upgrade — 실패해도 traceback 전체를 쏟지 않고 마지막 몇 줄(핵심 에러) + 임시 로그 경로만 안내.
function Invoke-AlembicUpgrade {
  if ($SkipInstall) {
    Write-Warn2 "SkipInstall: alembic 미실행. '.\.venv\Scripts\python -m alembic upgrade head'"
    return
  }
  if (-not (Test-Path -LiteralPath $venvPy)) {
    Write-Warn2 "venv 미설치 — '.\.venv\Scripts\python -m alembic upgrade head' 수동 실행"
    Add-Incomplete "테이블 생성 (alembic — venv 없음)"
    return
  }
  Write-Step "Alembic: 테이블 생성 (upgrade head) — DB는 항상 Alembic으로 관리 §11"
  # ⛔ alembic 은 정상 진행 로그(INFO)도 stderr 로 쓴다. PS 5.1 은 EAP=Stop 아래에서 리다이렉트된
  #    네이티브 stderr 첫 줄을 NativeCommandError 로 종료 예외화해, 성공한 마이그레이션도 실패로 보고
  #    (심하면 도중에 끊고) 만다. 함수 스코프에서만 Continue 로 낮추고 판정은 $LASTEXITCODE 로만 한다.
  $ErrorActionPreference = 'Continue'
  $_alembicLog = [System.IO.Path]::GetTempFileName()
  $_rc = 1
  Push-Location -LiteralPath $Target
  try {
    # 모든 스트림(*>)을 로그 파일로 — 성공 시 조용히, 실패 시에만 마지막 몇 줄을 보여준다.
    & $venvPy -m alembic upgrade head *> $_alembicLog
    $_rc = $LASTEXITCODE
  } catch {
    Add-Content -LiteralPath $_alembicLog -Value $_.Exception.Message
    $_rc = 1
  } finally { Pop-Location }
  if ($_rc -eq 0) {
    Write-Ok "테이블 생성 완료"
    Remove-Item -LiteralPath $_alembicLog -ErrorAction SilentlyContinue
  } else {
    Write-Warn2 "alembic 실패 — 핵심 오류(마지막 6줄):"
    Get-Content -LiteralPath $_alembicLog -Tail 6 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "        $_" }
    Write-Warn2 "전체 로그: $_alembicLog"
    Write-Warn2 "수동 재실행: .\.venv\Scripts\python -m alembic upgrade head"
    Add-Incomplete "테이블 생성 (alembic upgrade head)"
  }
}
if (-not $SkipDb) {
  Write-Step "PostgreSQL: 데이터베이스 생성"
  Enable-Psql
  $psql = Get-Command psql -ErrorAction SilentlyContinue
  if (-not $psql) {
    Write-Warn2 "PostgreSQL 이 설치돼 있다면 bin 디렉터리를 PATH 에 추가하세요 (예: C:\Program Files\PostgreSQL\<버전>\bin)."
    Show-DbManualGuide "psql 없음(PATH·표준 설치 경로 모두)" "DB 생성·마이그레이션 (psql 없음)"
  } elseif ($DbUnreachable) {
    # 사전 검사에서 이미 접속 불가로 판정 — 조회/생성/alembic 모두 생략하고 안내만.
    Show-DbUnreachableGuide
  } else {
    $_q = Invoke-PsqlScript "SELECT 1 FROM pg_database WHERE datname = :'dbname';" -Tuples
    if (-not $_q.Ok) {
      # 사전 검사 이후 접속이 끊긴 경우 — 접속 실패로 보고 CREATE·alembic 모두 건너뛴다.
      Show-DbUnreachableGuide
    } elseif ($_q.Out -eq "1") {
      Write-Warn2 "DB 이미 존재: $DbName"
      Invoke-AlembicUpgrade
    } elseif ((Invoke-PsqlScript 'CREATE DATABASE :"dbname";').Ok) {
      Write-Ok "DB 생성: $DbName"
      # ⛔ 공통 계층은 세션 시각대 KST 를 전제한다(ARCHITECTURE.md KST 단일 기준). 앱 연결은 스스로
      #    맞추지만 psql·ETL 같은 외부 접속도 KST 로 보이도록 DB 기본값을 고정한다.
      if ((Invoke-PsqlScript "ALTER DATABASE :`"dbname`" SET timezone TO 'Asia/Seoul';").Ok) {
        Write-Ok "DB 기본 시각대: Asia/Seoul"
      } else {
        Write-Warn2 "DB 시각대 설정 실패 — 수동: ALTER DATABASE `"$DbName`" SET timezone TO 'Asia/Seoul'"
        Add-Incomplete "DB 기본 시각대 설정 (ALTER DATABASE … timezone)"
      }
      Invoke-AlembicUpgrade
    } else {
      Write-Warn2 "DB 생성 실패 — 접속정보 확인 후 수동으로 DB 생성/alembic 실행"
      Add-Incomplete "DB 생성 (CREATE DATABASE)"
    }
  }
} else { Write-Warn2 "SkipDb: DB 생성/마이그레이션 건너뜀" }

# ---------- 9. CSS 빌드 (Tailwind standalone CLI) ----------
# CLI 는 생성 프로젝트의 .tools\ 에 내려받고 scripts\tailwind-sha256sums.txt 로 검증한다(Node 불필요).
# PS 5.1 은 EAP=Stop + 네이티브 stderr 조합에서 NativeCommandError 로 죽을 수 있다(tailwindcss 는 진행
# 로그를 stderr 로 쓴다) — 함수 스코프에서만 Continue 로 낮추고 판정은 종료 코드로만 한다.
function Invoke-CssBuild {
  $ErrorActionPreference = 'Continue'
  $global:LASTEXITCODE = 0
  Push-Location -LiteralPath $Target
  try {
    & (Join-Path $Target 'scripts\tailwind.ps1')
    return $LASTEXITCODE
  } catch {
    Write-Warn2 "tailwind.ps1 실행 오류: $($_.Exception.Message)"
    return 1
  } finally { Pop-Location }
}
if (-not $SkipInstall) {
  Write-Step "CSS 빌드 (Tailwind standalone CLI)"
  $_cssRc = Invoke-CssBuild
  if ($_cssRc -eq 0) {
    Write-Ok "app\static\css\app.css 빌드 완료"
  } else {
    Write-Warn2 "CSS 빌드 미완료 — 네트워크 확인 후 '.\scripts\tailwind.ps1' 로 다시 실행하세요"
    Add-Incomplete "CSS 빌드 (Tailwind)"
  }
  $global:LASTEXITCODE = 0
} else { Write-Warn2 "SkipInstall: CSS 빌드 건너뜀" }

# ---------- 10. 실행 안내 ----------
Write-Step "실행 방법"
# -SkipInstall 은 사용자가 고른 생략이라 미완료(종료 코드 2)로 세지 않는다. 대신 아래 [앱] 명령이 쓰는
# venv 가 없으므로 생략한 설치 단계를 먼저 안내한다(scaffold.sh 와 같다).
if ($SkipInstall) {
  Write-Host "[설치]    -SkipInstall 로 생략한 단계를 먼저 실행 (Python $_minPython 이상):" -ForegroundColor White
  Write-Host "  cd `"$Target`"" -ForegroundColor White
  Write-Host "  python -m venv .venv" -ForegroundColor White
  Write-Host "  .\.venv\Scripts\python -m pip install --require-hashes -r requirements.lock" -ForegroundColor White
  if (-not $SkipDb) { Write-Host "  .\.venv\Scripts\python -m alembic upgrade head" -ForegroundColor White }
  Write-Host "  .\scripts\tailwind.ps1" -ForegroundColor White
  Write-Host ""
}
# venv 의 python 을 직접 호출한다 — Activate.ps1 은 실행 정책(Restricted 등)에 막힐 수 있다.
Write-Host @"
[앱]      새 PowerShell 터미널에서:
  cd "$Target"
  .\.venv\Scripts\python -m flask --app app.main run --debug --port $AppPort

[CSS]     템플릿을 고치는 동안 또 다른 터미널에서 (macOS/Linux 는 ./scripts/tailwind.sh --watch):
  cd "$Target"
  .\scripts\tailwind.ps1 -Watch

[로그인]  초기 관리자 계정 (.env 의 DEFAULT_ADMIN_PASSWORD):
  아이디: admin
  비밀번호: $seedAdminPw
$DeployNote

[확인]    브라우저: http://localhost:$AppPort
          → 공개 홈 화면이 보이면 성공입니다. admin 으로 로그인한 뒤 관리자 대시보드에서
            'DB 정상'과 마이그레이션 리비전이 보이는지 확인하세요.

[DB 변경] 모델 수정 시 (ARCHITECTURE.md §11):
  cd "$Target"
  .\.venv\Scripts\python -m alembic revision --autogenerate -m "변경요약"
  .\.venv\Scripts\python -m alembic upgrade head
"@ -ForegroundColor White

# ---------- 결과 요약 ----------
Write-Step "결과 요약"
if ($script:Incomplete.Count -gt 0) {
  Write-Warn2 "골격은 생성됐지만 미완료 단계가 $($script:Incomplete.Count)개 있습니다 — 위 안내대로 마무리하세요 (종료 코드 2):"
  foreach ($m in $script:Incomplete) { Write-Host "        - $m" -ForegroundColor Yellow }
  exit 2
}
Write-Ok "모든 단계 완료"
exit 0
