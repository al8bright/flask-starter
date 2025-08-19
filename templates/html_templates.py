"""
HTML 템플릿들 (Tailwind CSS 사용)
"""

# 사용하지 않는 템플릿들 (참고용으로 보관)
# BASE_BOOTSTRAP = """<!doctype html>
# <html lang="ko">
#   <head>
#     <meta charset="utf-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1">
#     <title>{{ title or '__PROJECT_NAME__' }}</title>
#     <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
#     <link href="{{ url_for('static', filename='css/styles.css') }}" rel="stylesheet">
#   </head>
#   <body>
#     <nav class="navbar navbar-expand-lg bg-body-tertiary">
#       <div class="container">
#         <a class="navbar-brand" href="/">__PROJECT_NAME__</a>
#       </div>
#     </nav>
#     <main class="container py-4">
#       {% block content %}{% endblock %}
#     </main>
#     <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
#     <script src="{{ url_for('static', filename='js/app.js') }}"></script>
#   </body>
# </html>
# """

# 기본 템플릿 (Tailwind CSS 사용 + 다국어 + 다크모드)
BASE_TAILWIND = """<!doctype html>
<html lang="{{ get_locale().language }}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title or _('__PROJECT_NAME__') }}</title>
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
    <header class="bg-white dark:bg-gray-800 shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center py-4">
          <div class="flex items-center space-x-4">
            <a href="{{ url_for('posts.list') }}" class="text-xl font-semibold text-gray-900 dark:text-white">
              {{ _('__PROJECT_NAME__') }}
            </a>
            <!-- 언어 선택 -->
            <div class="flex items-center space-x-2">
              <a href="{{ url_for('main.set_locale', locale='ko') }}" class="text-sm px-2 py-1 rounded {{ 'bg-blue-500 text-white' if get_locale().language == 'ko' else 'text-gray-600 dark:text-gray-400' }}">
                한국어
              </a>
              <a href="{{ url_for('main.set_locale', locale='en') }}" class="text-sm px-2 py-1 rounded {{ 'bg-blue-500 text-white' if get_locale().language == 'en' else 'text-gray-600 dark:text-gray-400' }}">
                English
              </a>
            </div>
          </div>
          <nav class="flex items-center space-x-4">
            <a href="{{ url_for('posts.list') }}" class="text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-3 py-2 rounded-md text-sm font-medium">
              {{ _('Posts') }}
            </a>
            {% if current_user.is_authenticated %}
              <a href="{{ url_for('posts.new') }}" class="text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-3 py-2 rounded-md text-sm font-medium">
                {{ _('Write Post') }}
              </a>
              <span class="text-gray-500 dark:text-gray-400 px-3 py-2 text-sm">
                {{ current_user.username }}{{ _('님') }}
              </span>
              <a href="{{ url_for('auth.logout') }}" class="text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-3 py-2 rounded-md text-sm font-medium">
                {{ _('Logout') }}
              </a>
            {% else %}
              <a href="{{ url_for('auth.login') }}" class="text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-3 py-2 rounded-md text-sm font-medium">
                {{ _('Login') }}
              </a>
            {% endif %}
            <!-- 테마 토글 버튼 -->
            <button id="theme-toggle" class="p-2 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors">
              <svg id="sun-icon" class="w-5 h-5 text-gray-800 dark:text-gray-200 hidden" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clip-rule="evenodd"></path>
              </svg>
              <svg id="moon-icon" class="w-5 h-5 text-gray-800 dark:text-gray-200" fill="currentColor" viewBox="0 0 20 20">
                <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path>
              </svg>
            </button>
          </nav>
        </div>
      </div>
    </header>
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {% block content %}{% endblock %}
    </main>
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
  </body>
</html>
"""

# BASE_MINIMAL = """<!doctype html>
# <html lang="ko">
#   <head>
#     <meta charset="utf-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1">
#     <title>{{ title or '__PROJECT_NAME__' }}</title>
#     <link href="{{ url_for('static', filename='css/styles.css') }}" rel="stylesheet">
#   </head>
#   <body>
#     <main class="container">
#       {% block content %}{% endblock %}
#     </main>
#     <script src="{{ url_for('static', filename='js/app.js') }}"></script>
#   </body>
# </html>
# """

INDEX_HTML = """{% extends 'base.html' %}
{% block content %}
<div class="text-center py-12">
  <h1 class="text-4xl font-bold text-gray-900 mb-4">🚀 __PROJECT_NAME__</h1>
  <p class="text-lg text-gray-600 mb-8">Flask 기반 게시판 애플리케이션</p>
  
  <div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
    <div class="bg-white p-6 rounded-lg shadow-md">
      <h3 class="text-xl font-semibold mb-2">📝 게시글 관리</h3>
      <p class="text-gray-600 mb-4">CRUD 기능이 완비된 게시판</p>
      <a href="{{ url_for('posts.list') }}" class="inline-block bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">게시글 보기</a>
    </div>
    
    <div class="bg-white p-6 rounded-lg shadow-md">
      <h3 class="text-xl font-semibold mb-2">🔐 사용자 인증</h3>
      <p class="text-gray-600 mb-4">로그인/로그아웃 기능</p>
      {% if current_user.is_authenticated %}
        <span class="inline-block bg-green-500 text-white px-4 py-2 rounded">로그인됨</span>
      {% else %}
        <a href="{{ url_for('auth.login') }}" class="inline-block bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">로그인</a>
      {% endif %}
    </div>
    
    <div class="bg-white p-6 rounded-lg shadow-md">
      <h3 class="text-xl font-semibold mb-2">📁 파일 업로드</h3>
      <p class="text-gray-600 mb-4">파일 첨부 및 다운로드</p>
      <a href="{{ url_for('posts.new') }}" class="inline-block bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600">글쓰기</a>
    </div>
  </div>
</div>
{% endblock %}
"""
