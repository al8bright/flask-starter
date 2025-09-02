"""
정적 파일 템플릿들
"""
from textwrap import dedent

STYLES_CSS = dedent(
    """
    /* Add your styles here */
    .container { max-width: 900px; margin: 0 auto; padding: 1rem; }
    """
)

APP_JS = """// 다크모드 토글 기능
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    const sunIcon = document.getElementById('sun-icon');
    const moonIcon = document.getElementById('moon-icon');
    
    // 저장된 테마 불러오기
    const currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.classList.toggle('dark', currentTheme === 'dark');
    updateIcon(currentTheme === 'dark');
    
    // 테마 토글 이벤트
    themeToggle.addEventListener('click', function() {
        const isDark = document.documentElement.classList.toggle('dark');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        updateIcon(isDark);
    });
    
    // 아이콘 업데이트 함수
    function updateIcon(isDark) {
        if (isDark) {
            sunIcon.classList.remove('hidden');
            moonIcon.classList.add('hidden');
        } else {
            sunIcon.classList.add('hidden');
            moonIcon.classList.remove('hidden');
        }
    }
    
    // 시스템 테마 감지 (선택사항)
    if (!localStorage.getItem('theme')) {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        document.documentElement.classList.toggle('dark', prefersDark);
        updateIcon(prefersDark);
    }
});

// 모바일 메뉴 토글 기능
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (mobileMenuToggle && mobileMenu) {
        mobileMenuToggle.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
        
        // 화면 크기 변경 시 모바일 메뉴 숨김
        window.addEventListener('resize', function() {
            if (window.innerWidth >= 640) { // sm 브레이크포인트
                mobileMenu.classList.add('hidden');
            }
        });
        
        // 메뉴 외부 클릭 시 메뉴 닫기
        document.addEventListener('click', function(e) {
            if (!mobileMenuToggle.contains(e.target) && !mobileMenu.contains(e.target)) {
                mobileMenu.classList.add('hidden');
            }
        });
    }
});

// 플래시 메시지 자동 숨김
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            setTimeout(function() {
                message.remove();
            }, 300);
        }, 3000);
    });
});

// 폼 유효성 검사
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(function(field) {
                if (!field.value.trim()) {
                    field.classList.add('border-red-500');
                    isValid = false;
                } else {
                    field.classList.remove('border-red-500');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert('필수 필드를 모두 입력해주세요.');
            }
        });
    });
});

// 스크롤 시 헤더 스타일 변경
document.addEventListener('DOMContentLoaded', function() {
    const header = document.querySelector('header');
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > 10) {
            header.classList.add('shadow-lg');
            header.classList.add('backdrop-blur-sm');
            header.classList.add('bg-white/95');
            header.classList.add('dark:bg-gray-800/95');
        } else {
            header.classList.remove('shadow-lg');
            header.classList.remove('backdrop-blur-sm');
            header.classList.remove('bg-white/95');
            header.classList.remove('dark:bg-gray-800/95');
        }
    });
});
"""

README = dedent(
    """
    # __PROJECT_NAME__

    Flask 기반 게시판 애플리케이션 (CRUD + 파일 업로드 + 인증)

    ## 기능

    - 🔐 사용자 인증 (로그인/로그아웃)
    - 📝 게시글 CRUD (생성/조회/수정/삭제)
    - 📁 파일 업로드 및 다운로드
    - 🎨 Tailwind CSS UI
    - ⚡ Flask-Caching
    - 🔄 환경별 설정 (개발/테스트/프로덕션)

    ## 설치 및 실행

    ```bash
    # 1) 가상환경 활성화
    # macOS/Linux
    source venv/bin/activate
    # Windows
    venv\\Scripts\\activate

    # 2) 데이터베이스 마이그레이션
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade

    # 3) 애플리케이션 실행
    flask run
    # 또는
    python wsgi.py
    ```

    ## 환경 설정

    `.env` 파일에서 다음 설정을 변경할 수 있습니다:

    ```env
    FLASK_ENV=development  # development, testing, production
    DATABASE_URL=sqlite:///app.db
    SECRET_KEY=your-secret-key
    ```

    ## 기본 사용자

    - 사용자명: admin
    - 비밀번호: admin123

    ## 프로젝트 구조

    ```
    app/
    ├── config.py          # 환경별 설정
    ├── extensions.py      # Flask 확장
    ├── routes/           # 라우트 블루프린트
    ├── models/           # 데이터베이스 모델
    ├── services/         # 비즈니스 로직
    ├── utils/            # 유틸리티 함수
    ├── templates/        # HTML 템플릿
    ├── static/           # 정적 파일
    └── uploads/          # 업로드된 파일
    ```
    """
)
