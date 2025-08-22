"""
HTML 템플릿들 (Tailwind CSS 사용)
"""

# 플래시 메시지 템플릿
FLASH_MESSAGES_HTML = """{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    {% for category, message in messages %}
      <div class="mb-6 bg-{{ 'red' if category == 'error' else 'green' }}-50 dark:bg-{{ 'red' if category == 'error' else 'green' }}-900/20 border border-{{ 'red' if category == 'error' else 'green' }}-200 dark:border-{{ 'red' if category == 'error' else 'green' }}-700 text-{{ 'red' if category == 'error' else 'green' }}-700 dark:text-{{ 'red' if category == 'error' else 'green' }}-300 px-4 py-3 rounded-lg flex items-center justify-between">
        <div class="flex items-center">
          {% if category == 'error' %}
            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
            </svg>
          {% else %}
            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
            </svg>
          {% endif %}
          <span class="font-medium">{{ message }}</span>
        </div>
        <button type="button" class="text-{{ 'red' if category == 'error' else 'green' }}-500 hover:text-{{ 'red' if category == 'error' else 'green' }}-700 dark:text-{{ 'red' if category == 'error' else 'green' }}-400 dark:hover:text-{{ 'red' if category == 'error' else 'green' }}-300" onclick="this.parentElement.remove()">
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
          </svg>
        </button>
      </div>
    {% endfor %}
  {% endif %}
{% endwith %}"""

# 기본 템플릿 (Tailwind CSS 사용 + 다크모드 + 반응형)
BASE_TAILWIND = """<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title or '__PROJECT_NAME__' }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
      tailwind.config = {
        darkMode: 'class',
        theme: {
          extend: {
            typography: {
              DEFAULT: {
                css: {
                  maxWidth: 'none',
                }
              }
            }
          }
        }
      }
    </script>
  </head>
  <body class="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 transition-colors duration-200">
    <!-- 헤더 -->
    <header class="bg-white dark:bg-gray-800 shadow-lg sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center py-3 lg:py-4">
          <!-- 로고 영역 -->
          <div class="flex items-center">
            <a href="{{ url_for('main.index') }}" class="text-lg lg:text-xl font-bold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition-colors duration-200">
              🚀 __PROJECT_NAME__
            </a>
          </div>
          
          <!-- 네비게이션 -->
          <nav class="hidden sm:flex items-center space-x-2 lg:space-x-4">
            <a href="{{ url_for('posts.list') }}" class="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 px-2 lg:px-3 py-2 rounded-lg text-sm lg:text-base font-medium transition-colors duration-200">
              📝 게시글
            </a>
            {% if current_user.is_authenticated %}
              <a href="{{ url_for('posts.new') }}" class="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 px-2 lg:px-3 py-2 rounded-lg text-sm lg:text-base font-medium transition-colors duration-200">
                ✏️ 글쓰기
              </a>
              <span class="text-gray-500 dark:text-gray-400 px-2 lg:px-3 py-2 text-sm lg:text-base">
                👤 {{ current_user.username }}님
              </span>
              <a href="{{ url_for('auth.logout') }}" class="text-gray-700 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400 px-2 lg:px-3 py-2 rounded-lg text-sm lg:text-base font-medium transition-colors duration-200">
                🚪 로그아웃
              </a>
            {% else %}
              <a href="{{ url_for('auth.login') }}" class="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 px-2 lg:px-3 py-2 rounded-lg text-sm lg:text-base font-medium transition-colors duration-200">
                🔐 로그인
              </a>
            {% endif %}
            
            <!-- 테마 토글 버튼 -->
            <button id="theme-toggle" class="p-2 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors duration-200">
              <svg id="sun-icon" class="w-4 h-4 lg:w-5 lg:h-5 text-gray-800 dark:text-gray-200 hidden" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clip-rule="evenodd"></path>
              </svg>
              <svg id="moon-icon" class="w-4 h-4 lg:w-5 lg:h-5 text-gray-800 dark:text-gray-200" fill="currentColor" viewBox="0 0 20 20">
                <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path>
              </svg>
            </button>
          </nav>
          
          <!-- 모바일 메뉴 버튼 -->
          <div class="sm:hidden">
            <button id="mobile-menu-toggle" class="p-2 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors duration-200">
              <svg class="w-5 h-5 text-gray-800 dark:text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
              </svg>
            </button>
          </div>
        </div>
        
        <!-- 모바일 메뉴 -->
        <div id="mobile-menu" class="hidden sm:hidden pb-4 border-t border-gray-200 dark:border-gray-700">
          <div class="flex flex-col space-y-2 pt-4">
            <a href="{{ url_for('posts.list') }}" class="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 px-3 py-2 rounded-lg text-base font-medium transition-colors duration-200">
              📝 게시글
            </a>
            {% if current_user.is_authenticated %}
              <a href="{{ url_for('posts.new') }}" class="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 px-3 py-2 rounded-lg text-base font-medium transition-colors duration-200">
                ✏️ 글쓰기
              </a>
              <span class="text-gray-500 dark:text-gray-400 px-3 py-2 text-base">
                👤 {{ current_user.username }}님
              </span>
              <a href="{{ url_for('auth.logout') }}" class="text-gray-700 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400 px-3 py-2 rounded-lg text-base font-medium transition-colors duration-200">
                🚪 로그아웃
              </a>
            {% else %}
              <a href="{{ url_for('auth.login') }}" class="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 px-3 py-2 rounded-lg text-base font-medium transition-colors duration-200">
                🔐 로그인
              </a>
            {% endif %}
          </div>
        </div>
      </div>
    </header>
    
    <!-- 메인 콘텐츠 -->
    <main class="flex-1">
      {% block content %}{% endblock %}
    </main>
    
    <!-- Footer -->
    <footer class="bg-gray-900 text-white py-6 lg:py-8 mt-16">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center">
          <div class="mb-4 lg:mb-6">
            <h3 class="text-lg lg:text-xl font-bold mb-1 lg:mb-2">🏢 개발팀</h3>
            <p class="text-gray-400 text-sm lg:text-base">작성자 | 2025년</p>
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 lg:gap-6 max-w-2xl mx-auto mb-4 lg:mb-6">
            <div class="text-center">
              <h4 class="font-semibold mb-1 lg:mb-2 text-sm lg:text-base">📧 이메일</h4>
              <a href="mailto:contact@example.com" 
                 class="text-blue-400 hover:text-blue-300 transition-colors text-sm lg:text-base break-all">
                contact@example.com
              </a>
            </div>
            <div class="text-center">
              <h4 class="font-semibold mb-1 lg:mb-2 text-sm lg:text-base">📞 연락처</h4>
              <a href="tel:010-0000-0000" 
                 class="text-blue-400 hover:text-blue-300 transition-colors text-sm lg:text-base">
                010-0000-0000
              </a>
            </div>
          </div>
          
          <div class="pt-4 lg:pt-6 border-t border-gray-700">
            <p class="text-gray-400 text-xs lg:text-sm">
              © 2025 개발팀. All rights reserved. | 
              <span class="text-blue-400">__PROJECT_NAME__</span> v1.0
            </p>
          </div>
        </div>
      </div>
    </footer>
    
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
  </body>
</html>
"""

INDEX_HTML = """{% extends 'base.html' %}
{% block content %}
<!-- Hero Section -->
<div class="bg-gradient-to-r from-blue-600 to-indigo-700 text-white py-12 lg:py-20">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
    <h1 class="text-3xl sm:text-4xl lg:text-5xl font-bold mb-4 lg:mb-6">🚀 __PROJECT_NAME__</h1>
    <p class="text-lg sm:text-xl mb-6 lg:mb-8 max-w-3xl mx-auto leading-relaxed">
      현대적이고 직관적인 Flask 기반 게시판 플랫폼으로, 
      효율적인 커뮤니케이션과 콘텐츠 관리를 경험해보세요.
    </p>
    <div class="flex flex-col sm:flex-row justify-center items-center space-y-4 sm:space-y-0 sm:space-x-4">
      <a href="{{ url_for('posts.list') }}" 
         class="w-full sm:w-auto bg-white text-blue-600 px-6 lg:px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors duration-200 text-center">
        📝 게시글 보기
      </a>
      {% if not current_user.is_authenticated %}
        <a href="{{ url_for('auth.login') }}" 
           class="w-full sm:w-auto border-2 border-white text-white px-6 lg:px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-blue-600 transition-colors duration-200 text-center">
          🔐 로그인
        </a>
      {% endif %}
    </div>
  </div>
</div>

<!-- Features Section -->
<div class="py-12 lg:py-16 bg-gray-50 dark:bg-gray-800">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="text-center mb-8 lg:mb-12">
      <h2 class="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3 lg:mb-4">✨ 주요 기능</h2>
      <p class="text-base lg:text-lg text-gray-600 dark:text-gray-400">강력하고 사용하기 쉬운 기능들로 구성되어 있습니다</p>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
      <!-- 게시글 관리 -->
      <div class="bg-white dark:bg-gray-700 p-6 lg:p-8 rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-300">
        <div class="text-3xl lg:text-4xl mb-3 lg:mb-4">📝</div>
        <h3 class="text-lg lg:text-xl font-semibold mb-3 lg:mb-4 text-gray-900 dark:text-white">게시글 관리</h3>
        <p class="text-sm lg:text-base text-gray-600 dark:text-gray-400 mb-4 lg:mb-6 leading-relaxed">
          완전한 CRUD 기능을 갖춘 게시판으로, 글쓰기부터 수정, 삭제까지 
          모든 작업을 직관적으로 수행할 수 있습니다.
        </p>
        <ul class="text-xs lg:text-sm text-gray-600 dark:text-gray-400 space-y-1 lg:space-y-2 mb-4 lg:mb-6">
          <li>✅ 실시간 글 작성 및 수정</li>
          <li>✅ 파일 첨부 및 다운로드</li>
          <li>✅ 페이지네이션 지원</li>
          <li>✅ 작성자별 권한 관리</li>
        </ul>
        <a href="{{ url_for('posts.list') }}" 
           class="inline-block bg-blue-500 text-white px-4 lg:px-6 py-2 rounded-lg hover:bg-blue-600 transition-colors duration-200 text-sm lg:text-base">
          게시글 보기 →
        </a>
      </div>
      
      <!-- 사용자 인증 -->
      <div class="bg-white dark:bg-gray-700 p-6 lg:p-8 rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-300">
        <div class="text-3xl lg:text-4xl mb-3 lg:mb-4">🔐</div>
        <h3 class="text-lg lg:text-xl font-semibold mb-3 lg:mb-4 text-gray-900 dark:text-white">사용자 인증</h3>
        <p class="text-sm lg:text-base text-gray-600 dark:text-gray-400 mb-4 lg:mb-6 leading-relaxed">
          안전하고 신뢰할 수 있는 로그인 시스템으로 
          개인화된 서비스를 제공합니다.
        </p>
        <ul class="text-xs lg:text-sm text-gray-600 dark:text-gray-400 space-y-1 lg:space-y-2 mb-4 lg:mb-6">
          <li>✅ 보안 로그인 시스템</li>
          <li>✅ 세션 관리</li>
          <li>✅ 권한 기반 접근 제어</li>
          <li>✅ 로그인 상태 유지</li>
        </ul>
        {% if current_user.is_authenticated %}
          <span class="inline-block bg-green-500 text-white px-4 lg:px-6 py-2 rounded-lg text-sm lg:text-base">
            ✅ 로그인됨
          </span>
        {% else %}
          <a href="{{ url_for('auth.login') }}" 
             class="inline-block bg-green-500 text-white px-4 lg:px-6 py-2 rounded-lg hover:bg-green-600 transition-colors duration-200 text-sm lg:text-base">
            로그인 →
          </a>
        {% endif %}
      </div>
      
      <!-- 파일 관리 -->
      <div class="bg-white dark:bg-gray-700 p-6 lg:p-8 rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-300 md:col-span-2 lg:col-span-1">
        <div class="text-3xl lg:text-4xl mb-3 lg:mb-4">📁</div>
        <h3 class="text-lg lg:text-xl font-semibold mb-3 lg:mb-4 text-gray-900 dark:text-white">파일 관리</h3>
        <p class="text-sm lg:text-base text-gray-600 dark:text-gray-400 mb-4 lg:mb-6 leading-relaxed">
          게시글에 파일을 첨부하고 다운로드할 수 있는 
          완전한 파일 관리 시스템을 제공합니다.
        </p>
        <ul class="text-xs lg:text-sm text-gray-600 dark:text-gray-400 space-y-1 lg:space-y-2 mb-4 lg:mb-6">
          <li>✅ 안전한 파일 업로드</li>
          <li>✅ 다운로드 기능</li>
          <li>✅ 파일 형식 검증</li>
          <li>✅ 저장 공간 관리</li>
        </ul>
        <a href="{{ url_for('posts.new') }}" 
           class="inline-block bg-purple-500 text-white px-4 lg:px-6 py-2 rounded-lg hover:bg-purple-600 transition-colors duration-200 text-sm lg:text-base">
          글쓰기 →
        </a>
      </div>
    </div>
  </div>
</div>

<!-- About Section -->
<div class="py-12 lg:py-16 bg-white dark:bg-gray-900">
  <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
    <h2 class="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-6 lg:mb-8">🎯 사이트 목적</h2>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8 text-left">
      <div class="bg-gray-50 dark:bg-gray-800 p-6 rounded-xl">
        <h3 class="text-lg lg:text-xl font-semibold mb-3 lg:mb-4 text-gray-900 dark:text-white">💡 개발 목적</h3>
        <p class="text-sm lg:text-base text-gray-600 dark:text-gray-400 leading-relaxed">
          이 플랫폼은 Flask 프레임워크의 강력함을 활용하여 
          현대적이고 확장 가능한 웹 애플리케이션을 구축하는 
          방법을 보여주기 위해 개발되었습니다.
        </p>
      </div>
      <div class="bg-gray-50 dark:bg-gray-800 p-6 rounded-xl">
        <h3 class="text-lg lg:text-xl font-semibold mb-3 lg:mb-4 text-gray-900 dark:text-white">🛠️ 기술 스택</h3>
        <p class="text-sm lg:text-base text-gray-600 dark:text-gray-400 leading-relaxed">
          Flask, SQLAlchemy, Tailwind CSS, Flask-Login 등 
          최신 웹 기술을 활용하여 안정적이고 
          사용자 친화적인 인터페이스를 제공합니다.
        </p>
      </div>
    </div>
  </div>
</div>

<!-- Usage Section -->
<div class="py-12 lg:py-16 bg-gray-50 dark:bg-gray-800">
  <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
    <h2 class="text-2xl sm:text-3xl font-bold text-center text-gray-900 dark:text-white mb-8 lg:mb-12">📖 사용법</h2>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
      <div class="bg-white dark:bg-gray-700 p-6 rounded-xl shadow-lg">
        <h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">👤 사용자</h3>
        <ol class="text-sm lg:text-base text-gray-600 dark:text-gray-400 space-y-2 leading-relaxed">
          <li>1. 로그인하여 계정에 접속</li>
          <li>2. 게시글 목록에서 원하는 글 확인</li>
          <li>3. 글쓰기 버튼으로 새 게시글 작성</li>
          <li>4. 필요시 파일 첨부하여 업로드</li>
          <li>5. 작성한 글 수정 또는 삭제</li>
        </ol>
      </div>
      <div class="bg-white dark:bg-gray-700 p-6 rounded-xl shadow-lg">
        <h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-white">🔧 관리자</h3>
        <ol class="text-sm lg:text-base text-gray-600 dark:text-gray-400 space-y-2 leading-relaxed">
          <li>1. 기본 계정: admin / admin123</li>
          <li>2. 모든 게시글 관리 권한</li>
          <li>3. 사용자 계정 관리</li>
          <li>4. 시스템 설정 변경</li>
          <li>5. 데이터베이스 백업</li>
        </ol>
      </div>
    </div>
  </div>
</div>
{% endblock %}
"""
