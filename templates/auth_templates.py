"""
인증 관련 HTML 템플릿들
"""

LOGIN_HTML = """{% extends 'base.html' %}

{% block content %}
<div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
  <div class="max-w-md w-full space-y-8">
    <div>
      <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
        로그인
      </h2>
    </div>
    
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="bg-{{ 'red' if category == 'error' else 'blue' }}-100 border border-{{ 'red' if category == 'error' else 'blue' }}-400 text-{{ 'red' if category == 'error' else 'blue' }}-700 px-4 py-3 rounded">
            {{ message }}
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    
    <form class="mt-8 space-y-6" method="POST">
      <div class="rounded-md shadow-sm -space-y-px">
        <div>
          <label for="username" class="sr-only">사용자명</label>
          <input id="username" name="username" type="text" required 
                 class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm" 
                 placeholder="사용자명">
        </div>
        <div>
          <label for="password" class="sr-only">비밀번호</label>
          <input id="password" name="password" type="password" required 
                 class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm" 
                 placeholder="비밀번호">
        </div>
      </div>

      <div class="flex items-center justify-between">
        <div class="flex items-center">
          <input id="remember" name="remember" type="checkbox" 
                 class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded">
          <label for="remember" class="ml-2 block text-sm text-gray-900">
            로그인 상태 유지
          </label>
        </div>
      </div>

      <div>
        <button type="submit" 
                class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
          로그인
        </button>
      </div>
    </form>
  </div>
</div>
{% endblock %}
"""
