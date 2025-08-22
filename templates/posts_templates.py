"""
게시글 관련 HTML 템플릿들
"""

POSTS_LIST_HTML = """{% extends 'base.html' %}

{% block content %}
<div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8">
  <!-- 헤더 섹션 -->
  <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 lg:mb-8">
    <h1 class="text-2xl lg:text-3xl font-bold text-gray-900 dark:text-white mb-4 sm:mb-0">📝 게시글 목록</h1>
    {% if current_user.is_authenticated %}
      <a href="{{ url_for('posts.new') }}" 
         class="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 lg:px-6 rounded-lg transition-colors duration-200 text-sm lg:text-base">
        ✏️ 새 글 작성
      </a>
    {% endif %}
  </div>

  <!-- 플래시 메시지 -->
  {% include 'flash_messages.html' %}

  {% if pagination and pagination.items %}
    <!-- 게시글 목록 -->
    <div class="bg-white dark:bg-gray-800 shadow-lg rounded-xl overflow-hidden">
      <ul class="divide-y divide-gray-200 dark:divide-gray-700">
        {% for post in pagination.items %}
          <li class="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-200">
            <div class="px-4 py-4 sm:px-6 lg:px-8">
              <div class="flex flex-col sm:flex-row sm:items-center justify-between space-y-3 sm:space-y-0">
                <div class="flex-1 min-w-0">
                  <a href="{{ url_for('posts.detail', post_id=post.id) }}" 
                     class="block group">
                    <div class="flex items-center justify-between mb-2">
                      <h3 class="text-base lg:text-lg font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors duration-200 truncate">
                        {{ post.title }}
                      </h3>
                      {% if post.has_file %}
                        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 ml-2">
                          📎 첨부파일
                        </span>
                      {% endif %}
                    </div>
                    <div class="flex flex-col sm:flex-row sm:items-center text-sm text-gray-500 dark:text-gray-400 space-y-1 sm:space-y-0 sm:space-x-6">
                      <span class="flex items-center">
                        <span class="mr-1">👤</span>
                        {{ post.author.username }}
                      </span>
                      <span class="flex items-center">
                        <span class="mr-1">📅</span>
                        {{ post.created_at.strftime('%Y-%m-%d %H:%M') }}
                      </span>
                    </div>
                  </a>
                </div>
                {% if current_user.is_authenticated and current_user.id == post.user_id %}
                  <div class="flex-shrink-0">
                    <a href="{{ url_for('posts.edit', post_id=post.id) }}" 
                       class="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 text-sm font-medium transition-colors duration-200">
                      ✏️ 수정
                    </a>
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
      <div class="mt-8 flex items-center justify-between">
        <!-- 모바일 페이지네이션 -->
        <div class="flex justify-between w-full sm:hidden">
          {% if pagination.has_prev %}
            <a href="{{ url_for('posts.list', page=pagination.prev_num) }}" 
               class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-lg text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-200">
              ← 이전
            </a>
          {% endif %}
          {% if pagination.has_next %}
            <a href="{{ url_for('posts.list', page=pagination.next_num) }}" 
               class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-lg text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-200">
              다음 →
            </a>
          {% endif %}
        </div>
        
        <!-- 데스크톱 페이지네이션 -->
        <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
          <div>
            <p class="text-sm text-gray-700 dark:text-gray-300">
              <span class="font-medium">{{ pagination.page }}</span> / 
              <span class="font-medium">{{ pagination.pages }}</span> 페이지
            </p>
          </div>
          <div>
            <nav class="relative z-0 inline-flex rounded-lg shadow-sm -space-x-px">
              {% for page_num in pagination.iter_pages() %}
                {% if page_num %}
                  {% if page_num != pagination.page %}
                    <a href="{{ url_for('posts.list', page=page_num) }}" 
                       class="bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 relative inline-flex items-center px-3 py-2 border text-sm font-medium transition-colors duration-200">
                      {{ page_num }}
                    </a>
                  {% else %}
                    <span class="bg-blue-50 dark:bg-blue-900/20 border-blue-500 text-blue-600 dark:text-blue-400 relative inline-flex items-center px-3 py-2 border text-sm font-medium">
                      {{ page_num }}
                    </span>
                  {% endif %}
                {% else %}
                  <span class="bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400 relative inline-flex items-center px-3 py-2 border text-sm font-medium">
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
    <!-- 빈 상태 -->
    <div class="text-center py-12 lg:py-16">
      <div class="text-6xl mb-4">📝</div>
      <h3 class="text-lg lg:text-xl font-semibold text-gray-900 dark:text-white mb-2">게시글이 없습니다</h3>
      <p class="text-gray-500 dark:text-gray-400 mb-6">첫 번째 게시글을 작성해보세요!</p>
      {% if current_user.is_authenticated %}
        <a href="{{ url_for('posts.new') }}" 
           class="inline-flex items-center bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-lg transition-colors duration-200">
          ✏️ 첫 번째 글 작성하기
        </a>
      {% endif %}
    </div>
  {% endif %}
</div>
{% endblock %}
"""

POSTS_DETAIL_HTML = """{% extends 'base.html' %}

{% block content %}
<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8">
  <!-- 게시글 상세 -->
  <div class="bg-white dark:bg-gray-800 shadow-lg rounded-xl overflow-hidden">
    <!-- 헤더 -->
    <div class="px-4 py-6 sm:px-6 lg:px-8 border-b border-gray-200 dark:border-gray-700">
      <div class="flex flex-col lg:flex-row lg:justify-between lg:items-start space-y-4 lg:space-y-0">
        <div class="flex-1">
          <h1 class="text-xl lg:text-2xl font-bold text-gray-900 dark:text-white mb-2">
            {{ post.title }}
          </h1>
          <div class="flex flex-col sm:flex-row sm:items-center text-sm text-gray-500 dark:text-gray-400 space-y-1 sm:space-y-0 sm:space-x-6">
            <span class="flex items-center">
              <span class="mr-1">👤</span>
              {{ post.author.username }}
            </span>
            <span class="flex items-center">
              <span class="mr-1">📅</span>
              {{ post.created_at.strftime('%Y-%m-%d %H:%M') }}
            </span>
            {% if post.updated_at != post.created_at %}
              <span class="flex items-center">
                <span class="mr-1">✏️</span>
                수정됨: {{ post.updated_at.strftime('%Y-%m-%d %H:%M') }}
              </span>
            {% endif %}
          </div>
        </div>
        
        {% if current_user.is_authenticated and current_user.id == post.user_id %}
          <div class="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-3">
            <a href="{{ url_for('posts.edit', post_id=post.id) }}" 
               class="inline-flex items-center justify-center bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold py-2 px-4 rounded-lg transition-colors duration-200">
              ✏️ 수정
            </a>
            <form method="POST" action="{{ url_for('posts.delete', post_id=post.id) }}" 
                  onsubmit="return confirm('정말 삭제하시겠습니까?')" class="inline">
              <button type="submit" 
                      class="inline-flex items-center justify-center bg-red-600 hover:bg-red-700 text-white text-sm font-semibold py-2 px-4 rounded-lg transition-colors duration-200">
                🗑️ 삭제
              </button>
            </form>
          </div>
        {% endif %}
      </div>
    </div>
    
    <!-- 본문 -->
    <div class="px-4 py-6 sm:px-6 lg:px-8">
      <div class="prose prose-lg max-w-none dark:prose-invert">
        <div class="text-gray-900 dark:text-gray-100 leading-relaxed whitespace-pre-wrap">
          {{ post.content | nl2br }}
        </div>
      </div>
      
      {% if post.has_file %}
        <div class="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">📎 첨부파일</h3>
          <a href="{{ url_for('files.download', post_id=post.id) }}" 
             class="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-lg text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors duration-200">
            📥 {{ post.filename }} 다운로드
          </a>
        </div>
      {% endif %}
    </div>
  </div>
  
  <!-- 하단 버튼 -->
  <div class="mt-6 lg:mt-8 flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4">
    <a href="{{ url_for('posts.list') }}" 
       class="inline-flex items-center justify-center bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 px-6 rounded-lg transition-colors duration-200">
      ← 목록으로 돌아가기
    </a>
    {% if current_user.is_authenticated %}
      <a href="{{ url_for('posts.new') }}" 
         class="inline-flex items-center justify-center bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-lg transition-colors duration-200">
        ✏️ 새 글 작성
      </a>
    {% endif %}
  </div>
</div>
{% endblock %}
"""

POSTS_FORM_HTML = """{% extends 'base.html' %}

{% block content %}
<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-8">
  <!-- 폼 컨테이너 -->
  <div class="bg-white dark:bg-gray-800 shadow-lg rounded-xl overflow-hidden">
    <!-- 헤더 -->
    <div class="px-4 py-6 sm:px-6 lg:px-8 border-b border-gray-200 dark:border-gray-700">
      <h1 class="text-xl lg:text-2xl font-bold text-gray-900 dark:text-white">
        {% if post %}✏️ 게시글 수정{% else %}✏️ 새 게시글 작성{% endif %}
      </h1>
      <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
        {% if post %}게시글을 수정합니다.{% else %}새로운 게시글을 작성합니다.{% endif %}
      </p>
    </div>
    
    <!-- 폼 -->
    <form method="POST" enctype="multipart/form-data" class="px-4 py-6 sm:px-6 lg:px-8">
      <!-- 플래시 메시지 -->
      {% include 'flash_messages.html' %}
      
      <div class="space-y-6">
        <!-- 제목 필드 -->
        <div>
          <label for="title" class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            📝 제목 <span class="text-red-500">*</span>
          </label>
          <input type="text" name="title" id="title" required
                 value="{{ post.title if post else '' }}"
                 placeholder="게시글 제목을 입력하세요"
                 class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 transition-colors duration-200">
        </div>

        <!-- 내용 필드 -->
        <div>
          <label for="content" class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            📄 내용 <span class="text-red-500">*</span>
          </label>
          <textarea id="content" name="content" rows="12" required
                    placeholder="게시글 내용을 입력하세요"
                    class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 resize-y transition-colors duration-200">{{ post.content if post else '' }}</textarea>
        </div>

        <!-- 파일 첨부 필드 -->
        <div>
          <label for="file" class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            📎 첨부파일
          </label>
          <div class="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 dark:border-gray-600 border-dashed rounded-lg hover:border-gray-400 dark:hover:border-gray-500 transition-colors duration-200">
            <div class="space-y-1 text-center">
              <svg class="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              <div class="flex text-sm text-gray-600 dark:text-gray-400">
                <label for="file" class="relative cursor-pointer bg-white dark:bg-gray-700 rounded-md font-medium text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-blue-500">
                  <span>파일 선택</span>
                  <input id="file" name="file" type="file" class="sr-only">
                </label>
                <p class="pl-1">또는 드래그 앤 드롭</p>
              </div>
              <p class="text-xs text-gray-500 dark:text-gray-400">
                PNG, JPG, GIF, PDF, DOC, XLS 최대 10MB
              </p>
            </div>
          </div>
          {% if post and post.has_file %}
            <div class="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
              <p class="text-sm text-blue-700 dark:text-blue-300">
                <span class="font-medium">현재 첨부파일:</span> {{ post.filename }}
              </p>
              <p class="text-xs text-blue-600 dark:text-blue-400 mt-1">
                새 파일을 선택하면 기존 파일이 교체됩니다.
              </p>
            </div>
          {% endif %}
        </div>
      </div>

      <!-- 버튼 영역 -->
      <div class="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row justify-end space-y-3 sm:space-y-0 sm:space-x-4">
        <a href="{{ url_for('posts.list') }}" 
           class="inline-flex items-center justify-center px-6 py-3 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-semibold rounded-lg text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200">
          ❌ 취소
        </a>
        <button type="submit" 
                class="inline-flex items-center justify-center px-6 py-3 border border-transparent text-sm font-semibold rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200">
          {% if post %}💾 수정 완료{% else %}📝 작성 완료{% endif %}
        </button>
      </div>
    </form>
  </div>
</div>
{% endblock %}
"""
