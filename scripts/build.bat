@echo off
setlocal enabledelayedexpansion

echo 🚀 Flask Builder 빌드 시작...

REM 색상 정의 (Windows 10+)
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "NC=[0m"

REM 함수 정의
:log_info
echo %GREEN%[INFO]%NC% %~1
goto :eof

:log_warn
echo %YELLOW%[WARN]%NC% %~1
goto :eof

:log_error
echo %RED%[ERROR]%NC% %~1
goto :eof

REM Python 의존성 확인
call :log_info "Python 설치 확인..."
python --version >nul 2>&1
if errorlevel 1 (
    python3 --version >nul 2>&1
    if errorlevel 1 (
        call :log_error "Python이 설치되어 있지 않습니다."
        exit /b 1
    )
)
call :log_info "Python 설치 확인 완료"

REM Node.js 의존성 확인
call :log_info "Node.js 설치 확인..."
node --version >nul 2>&1
if errorlevel 1 (
    call :log_error "Node.js가 설치되어 있지 않습니다."
    exit /b 1
)
call :log_info "Node.js 설치 확인 완료"

REM Python 의존성 설치
call :log_info "Python 의존성 설치..."
pip install -r requirements.txt
if errorlevel 1 (
    call :log_error "Python 의존성 설치 실패"
    exit /b 1
)
call :log_info "Python 의존성 설치 완료"

REM Node.js 의존성 설치
call :log_info "Node.js 의존성 설치..."
cd electron-app
call npm ci
if errorlevel 1 (
    call :log_error "Node.js 의존성 설치 실패"
    exit /b 1
)
cd ..
call :log_info "Node.js 의존성 설치 완료"

REM Electron 앱 빌드
call :log_info "Electron 앱 빌드..."
cd electron-app
call npm run build
if errorlevel 1 (
    call :log_error "Electron 앱 빌드 실패"
    exit /b 1
)
cd ..
call :log_info "Electron 앱 빌드 완료"

REM 배포 파일 생성
set "platform=%1"
if "%platform%"=="" set "platform=all"

call :log_info "%platform%용 배포 파일 생성..."
cd electron-app

if "%platform%"=="win" (
    call npm run dist:win
) else if "%platform%"=="mac" (
    call npm run dist:mac
) else if "%platform%"=="linux" (
    call npm run dist:linux
) else if "%platform%"=="all" (
    call npm run dist
) else (
    call :log_error "지원하지 않는 플랫폼: %platform%"
    exit /b 1
)

if errorlevel 1 (
    call :log_error "배포 파일 생성 실패"
    exit /b 1
)

cd ..
call :log_info "%platform%용 배포 파일 생성 완료"

call :log_info "🎉 빌드 완료!"
call :log_info "배포 파일 위치: electron-app/dist/"

pause
