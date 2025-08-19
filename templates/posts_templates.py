"""
게시글 관련 HTML 템플릿들
"""

POSTS_LIST_HTML = """{% extends 'base.html' %}

{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
  <div class="flex justify-between items-center mb-6">
    <h1 class="text-3xl font-bold text-gray-900">게시글 목록</h1>
    {% if current_user.is_authenticated %}
      <a href="{{ url_for('posts.new') }}" 
         class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
        새 글 작성
      </a>
    {% endif %}
  </div>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for category, message in messages %}
        <div class="mb-4 bg-{{ 'red' if category == 'error' else 'green' }}-100 border border-{{ 'red' if category == 'error' else 'green' }}-400 text-{{ 'red' if category == 'error' else 'green' }}-700 px-4 py-3 rounded">
          {{ message }}
        </div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  {% if pagination and pagination.items %}
    <div class="bg-white shadow overflow-hidden sm:rounded-md">
      <ul class="divide-y divide-gray-200">
        {% for post in pagination.items %}
          <li>
            <div class="px-4 py-4 sm:px-6">
              <div class="flex items-center justify-between">
                <div class="flex-1 min-w-0">
                  <a href="{{ url_for('posts.detail', post_id=post.id) }}" 
                     class="block hover:bg-gray-50">
                    <div class="flex items-center justify-between">
                      <p class="text-sm font-medium text-indigo-600 truncate">
                        {{ post.title }}
                      </p>
                      {% if post.has_file %}
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          📎 첨부파일
                        </span>
                      {% endif %}
                    </div>
                    <div class="mt-2 flex justify-between">
                      <div class="sm:flex">
                        <p class="flex items-center text-sm text-gray-500">
                          👤 {{ post.author.username }}
                        </p>
                        <p class="mt-2 flex items-center text-sm text-gray-500 sm:mt-0 sm:ml-6">
                          📅 {{ post.created_at.strftime('%Y-%m-%d %H:%M') }}
                        </p>
                      </div>
                    </div>
                  </a>
                </div>
                {% if current_user.is_authenticated and current_user.id == post.user_id %}
                  <div class="ml-4 flex-shrink-0 flex space-x-2">
                    <a href="{{ url_for('posts.edit', post_id=post.id) }}" 
                       class="text-indigo-600 hover:text-indigo-900 text-sm">수정</a>
                  </div>
                {% endif %}
              </div>
            </div>
          </li>
        {% endfor %}
      </ul>
    </div>

    <!-- 페이지네이션 -->
    {% if pagination.pages > 1 %}
      <div class="mt-6 flex items-center justify-between">
        <div class="flex-1 flex justify-between sm:hidden">
          {% if pagination.has_prev %}
            <a href="{{ url_for('posts.list', page=pagination.prev_num) }}" 
               class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
              이전
            </a>
          {% endif %}
          {% if pagination.has_next %}
            <a href="{{ url_for('posts.list', page=pagination.next_num) }}" 
               class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
              다음
            </a>
          {% endif %}
        </div>
        <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
          <div>
            <p class="text-sm text-gray-700">
              <span class="font-medium">{{ pagination.page }}</span> / 
              <span class="font-medium">{{ pagination.pages }}</span> 페이지
            </p>
          </div>
          <div>
            <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
              {% for page_num in pagination.iter_pages() %}
                {% if page_num %}
                  {% if page_num != pagination.page %}
                    <a href="{{ url_for('posts.list', page=page_num) }}" 
                       class="bg-white border-gray-300 text-gray-500 hover:bg-gray-50 relative inline-flex items-center px-4 py-2 border text-sm font-medium">
                      {{ page_num }}
                    </a>
                  {% else %}
                    <span class="bg-indigo-50 border-indigo-500 text-indigo-600 relative inline-flex items-center px-4 py-2 border text-sm font-medium">
                      {{ page_num }}
                    </span>
                  {% endif %}
                {% else %}
                  <span class="bg-white border-gray-300 text-gray-500 relative inline-flex items-center px-4 py-2 border text-sm font-medium">
                    ...
                  </span>
                {% endif %}
              {% endfor %}
            </nav>
          </div>
        </div>
      </div>
    {% endif %}
  {% else %}
    <div class="text-center py-12">
      <p class="text-gray-500 text-lg">게시글이 없습니다.</p>
      {% if current_user.is_authenticated %}
        <a href="{{ url_for('posts.new') }}" 
           class="mt-4 inline-block bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
          첫 번째 글 작성하기
        </a>
      {% endif %}
    </div>
  {% endif %}
</div>
{% endblock %}
"""

POSTS_DETAIL_HTML = """{% extends 'base.html' %}

{% block content %}
<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
  <div class="bg-white shadow overflow-hidden sm:rounded-lg">
    <div class="px-4 py-5 sm:px-6">
      <div class="flex justify-between items-start">
        <div>
          <h3 class="text-lg leading-6 font-medium text-gray-900">
            {{ post.title }}
          </h3>
          <p class="mt-1 max-w-2xl text-sm text-gray-500">
            작성자: {{ post.author.username }} | 작성일: {{ post.created_at.strftime('%Y-%m-%d %H:%M') }}
          </p>
        </div>
        {% if current_user.is_authenticated and current_user.id == post.user_id %}
          <div class="flex space-x-2">
            <a href="{{ url_for('posts.edit', post_id=post.id) }}" 
               class="bg-blue-500 hover:bg-blue-700 text-white text-sm font-bold py-2 px-4 rounded">
              수정
            </a>
            <form method="POST" action="{{ url_for('posts.delete', post_id=post.id) }}" 
                  onsubmit="return confirm('정말 삭제하시겠습니까?')" class="inline">
              <button type="submit" 
                      class="bg-red-500 hover:bg-red-700 text-white text-sm font-bold py-2 px-4 rounded">
                삭제
              </button>
            </form>
          </div>
        {% endif %}
      </div>
    </div>
    
    <div class="border-t border-gray-200">
      <div class="px-4 py-5 sm:p-6">
        <div class="prose max-w-none">
          {{ post.content | nl2br }}
        </div>
        
        {% if post.has_file %}
          <div class="mt-6 pt-6 border-t border-gray-200">
            <h4 class="text-lg font-medium text-gray-900 mb-2">첨부파일</h4>
            <a href="{{ url_for('files.download', post_id=post.id) }}" 
               class="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
              📎 {{ post.filename }} 다운로드
            </a>
          </div>
        {% endif %}
      </div>
    </div>
  </div>
  
  <div class="mt-6">
    <a href="{{ url_for('posts.list') }}" 
       class="bg-gray-500 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded">
      목록으로 돌아가기
    </a>
  </div>
</div>
{% endblock %}
"""

POSTS_FORM_HTML = """{% extends 'base.html' %}

{% block content %}
<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
  <div class="bg-white shadow overflow-hidden sm:rounded-lg">
    <div class="px-4 py-5 sm:px-6">
      <h3 class="text-lg leading-6 font-medium text-gray-900">
        {% if post %}게시글 수정{% else %}새 게시글 작성{% endif %}
      </h3>
    </div>
    
    <div class="border-t border-gray-200">
      <form method="POST" enctype="multipart/form-data" class="px-4 py-5 sm:p-6">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="mb-4 bg-{{ 'red' if category == 'error' else 'green' }}-100 border border-{{ 'red' if category == 'error' else 'green' }}-400 text-{{ 'red' if category == 'error' else 'green' }}-700 px-4 py-3 rounded">
                {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        
        <div class="grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-6">
          <div class="sm:col-span-6">
            <label for="title" class="block text-sm font-medium text-gray-700">
              제목
            </label>
            <div class="mt-1">
              <input type="text" name="title" id="title" required
                     value="{{ post.title if post else '' }}"
                     class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md">
            </div>
          </div>

          <div class="sm:col-span-6">
            <label for="content" class="block text-sm font-medium text-gray-700">
              내용
            </label>
            <div class="mt-1">
              <textarea id="content" name="content" rows="10" required
                        class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md">{{ post.content if post else '' }}</textarea>
            </div>
          </div>

          <div class="sm:col-span-6">
            <label for="file" class="block text-sm font-medium text-gray-700">
              첨부파일
            </label>
            <div class="mt-1">
              <input type="file" name="file" id="file"
                     class="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md">
            </div>
            {% if post and post.has_file %}
              <p class="mt-2 text-sm text-gray-500">
                현재 첨부파일: {{ post.filename }}
              </p>
            {% endif %}
          </div>
        </div>

        <div class="pt-5">
          <div class="flex justify-end space-x-3">
            <a href="{{ url_for('posts.list') }}" 
               class="bg-white py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
              취소
            </a>
            <button type="submit" 
                    class="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
              {% if post %}수정{% else %}작성{% endif %}
            </button>
          </div>
        </div>
      </form>
    </div>
  </div>
</div>
{% endblock %}
"""
