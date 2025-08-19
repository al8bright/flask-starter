#!/bin/bash

# Flask Builder 빌드 스크립트

set -e

echo "🚀 Flask Builder 빌드 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 함수 정의
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Python 의존성 확인
check_python() {
    log_info "Python 설치 확인..."
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        log_error "Python이 설치되어 있지 않습니다."
        exit 1
    fi
    log_info "Python 설치 확인 완료"
}

# Node.js 의존성 확인
check_node() {
    log_info "Node.js 설치 확인..."
    if ! command -v node &> /dev/null; then
        log_error "Node.js가 설치되어 있지 않습니다."
        exit 1
    fi
    log_info "Node.js 설치 확인 완료"
}

# Python 의존성 설치
install_python_deps() {
    log_info "Python 의존성 설치..."
    pip install -r requirements.txt
    log_info "Python 의존성 설치 완료"
}

# Node.js 의존성 설치
install_node_deps() {
    log_info "Node.js 의존성 설치..."
    cd electron-app
    npm ci
    cd ..
    log_info "Node.js 의존성 설치 완료"
}

# Electron 앱 빌드
build_electron() {
    log_info "Electron 앱 빌드..."
    cd electron-app
    npm run build
    cd ..
    log_info "Electron 앱 빌드 완료"
}

# 배포 파일 생성
build_distributable() {
    local platform=$1
    
    log_info "$platform용 배포 파일 생성..."
    cd electron-app
    
    case $platform in
        "win")
            npm run dist:win
            ;;
        "mac")
            npm run dist:mac
            ;;
        "linux")
            npm run dist:linux
            ;;
        "all")
            npm run dist
            ;;
        *)
            log_error "지원하지 않는 플랫폼: $platform"
            exit 1
            ;;
    esac
    
    cd ..
    log_info "$platform용 배포 파일 생성 완료"
}

# 메인 실행
main() {
    local platform=${1:-"all"}
    
    log_info "Flask Builder 빌드 프로세스 시작"
    
    # 의존성 확인
    check_python
    check_node
    
    # 의존성 설치
    install_python_deps
    install_node_deps
    
    # Electron 앱 빌드
    build_electron
    
    # 배포 파일 생성
    build_distributable $platform
    
    log_info "🎉 빌드 완료!"
    log_info "배포 파일 위치: electron-app/dist/"
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
