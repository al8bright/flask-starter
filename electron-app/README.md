# Flask Builder GUI 🖥️

Flask Builder의 그래픽 사용자 인터페이스입니다. CLI를 모르는 사용자도 쉽게 Flask 프로젝트를 생성할 수 있습니다.

## 🚀 주요 기능

- **🎯 직관적인 GUI**: 드래그 앤 드롭과 클릭으로 간편한 프로젝트 생성
- **📁 폴더 선택**: 시스템 파일 탐색기를 통한 프로젝트 경로 선택
- **🗄️ 데이터베이스 설정**: 드롭다운으로 간편한 DB 선택 및 설정
- **📋 실시간 로그**: 프로젝트 생성 과정을 실시간으로 확인
- **🔍 Python 설치 확인**: 자동으로 Python 설치 상태 확인

## 🛠️ 기술 스택

- **Electron**: 크로스 플랫폼 데스크톱 앱
- **React**: 사용자 인터페이스
- **Webpack**: 번들링 및 개발 서버
- **Python**: 백엔드 Flask Builder 연동

## 📦 설치 및 실행

### 개발 환경 설정

```bash
# 의존성 설치
npm install

# 개발 모드 실행
npm run dev
```

### 프로덕션 빌드

```bash
# 앱 빌드
npm run build

# 실행 파일 생성
npm run dist
```

### 플랫폼별 빌드

```bash
# Windows
npm run dist:win

# macOS
npm run dist:mac

# Linux
npm run dist:linux
```

## 🏗️ 프로젝트 구조

```
electron-app/
├── src/
│   ├── App.jsx          # 메인 React 컴포넌트
│   ├── App.css          # 스타일시트
│   ├── index.js         # React 진입점
│   └── index.html       # HTML 템플릿
├── main.js              # Electron 메인 프로세스
├── preload.js           # 보안 API 노출
├── package.json         # 프로젝트 설정
├── webpack.config.js    # Webpack 설정
└── README.md           # 이 파일
```

## 🔧 개발 가이드

### 새로운 기능 추가

1. **React 컴포넌트 수정**: `src/App.jsx`에서 UI 로직 수정
2. **스타일 수정**: `src/App.css`에서 CSS 스타일 수정
3. **Electron API 추가**: `main.js`에서 IPC 핸들러 추가
4. **보안 API 노출**: `preload.js`에서 API 노출

### Python Flask Builder 연동

Electron 앱은 Python Flask Builder와 다음과 같이 연동됩니다:

1. **설정 전달**: React에서 수집한 설정을 JSON으로 Python에 전달
2. **실행 모니터링**: Python 프로세스의 stdout/stderr를 실시간으로 수신
3. **결과 처리**: 성공/실패 상태를 UI에 반영

## 🎨 UI 컴포넌트

### 폼 섹션
- **프로젝트 설정**: 프로젝트 이름, 생성 경로
- **데이터베이스 설정**: DB 타입 선택 및 연결 정보

### 출력 섹션
- **실시간 로그**: Python 프로세스 출력 표시
- **상태 표시**: 성공/오류/진행 중 상태 표시

## 🔒 보안 고려사항

- **Context Isolation**: Node.js API를 직접 노출하지 않음
- **Preload Script**: 안전한 API만 노출
- **입력 검증**: 사용자 입력에 대한 적절한 검증

## 🐛 문제 해결

### Python이 감지되지 않는 경우
1. Python이 시스템 PATH에 추가되어 있는지 확인
2. `python --version` 명령어가 터미널에서 작동하는지 확인

### 프로젝트 생성 실패
1. 선택한 경로에 쓰기 권한이 있는지 확인
2. 인터넷 연결 상태 확인 (패키지 다운로드 필요)
3. 로그에서 구체적인 오류 메시지 확인

## 📝 라이선스

MIT License - 자세한 내용은 상위 디렉토리의 LICENSE 파일을 참조하세요.

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

⭐ 이 프로젝트가 도움이 되었다면 스타를 눌러주세요!
