"""
유틸리티 템플릿들
"""
from textwrap import dedent

STORAGE_UTILS = dedent(
    """
    import os
    import uuid
    from datetime import datetime
    from werkzeug.utils import secure_filename
    from flask import current_app
    
    
    def allowed_file(filename):
        '''허용된 파일 확장자인지 확인'''
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']
    
    
    def ensure_uploads_dir():
        '''uploads 디렉토리가 존재하는지 확인하고 없으면 생성'''
        uploads_dir = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
        return uploads_dir
    
    
    def save_upload(file, subfolder=''):
        '''파일을 업로드하고 저장 경로를 반환'''
        if file and allowed_file(file.filename):
            # 안전한 파일명 생성
            filename = secure_filename(file.filename)
            
            # 고유한 파일명 생성 (충돌 방지)
            name, ext = os.path.splitext(filename)
            unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
            
            # 업로드 디렉토리 확인
            uploads_dir = ensure_uploads_dir()
            
            # 서브폴더가 있으면 생성
            if subfolder:
                subfolder_path = os.path.join(uploads_dir, subfolder)
                if not os.path.exists(subfolder_path):
                    os.makedirs(subfolder_path)
                file_path = os.path.join(subfolder_path, unique_filename)
            else:
                file_path = os.path.join(uploads_dir, unique_filename)
            
            # 파일 저장
            file.save(file_path)
            
            return {
                'filename': filename,
                'saved_filename': unique_filename,
                'file_path': file_path,
                'relative_path': os.path.relpath(file_path, uploads_dir)
            }
        return None
    
    
    def delete_upload(file_path):
        '''업로드된 파일 삭제'''
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except OSError:
                return False
        return False
    """
)

PAGINATION_UTILS = dedent(
    """
    from flask import request, url_for
    
    
    class Pagination:
        '''페이지네이션 클래스'''
        
        def __init__(self, query, page, per_page=10, total=None):
            self.query = query
            self.page = page
            self.per_page = per_page
            self.total = total or query.count()
            self.items = query.limit(per_page).offset((page - 1) * per_page).all()
        
        @property
        def pages(self):
            '''전체 페이지 수'''
            return max(0, self.total - 1) // self.per_page + 1
        
        @property
        def has_prev(self):
            '''이전 페이지가 있는지'''
            return self.page > 1
        
        @property
        def has_next(self):
            '''다음 페이지가 있는지'''
            return self.page < self.pages
        
        @property
        def prev_num(self):
            '''이전 페이지 번호'''
            return self.page - 1
        
        @property
        def next_num(self):
            '''다음 페이지 번호'''
            return self.page + 1
        
        def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
            '''페이지 번호 반복자'''
            last = 0
            for num in range(1, self.pages + 1):
                if num <= left_edge or (num > self.page - left_current - 1 and num < self.page + right_current) or num > self.pages - right_edge:
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num
    """
)

LOGGING_UTILS = dedent(
    """
    import logging
    from logging.handlers import RotatingFileHandler
    import os
    

    def setup_logging(app):
        '''로깅 설정'''
        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = RotatingFileHandler('logs/app.log', maxBytes=1024*1024, backupCount=10, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('애플리케이션 시작')

        @app.errorhandler(Exception)
        def log_exceptions(error):
            app.logger.error(f'예외 발생: {str(error)}', exc_info=True)
            return None  
    """
)

ERRORS_UTILS = dedent(
    """
    from flask import render_template
    from werkzeug.exceptions import HTTPException
    
    
    def register_error_handlers(app):
        '''에러 핸들러 등록'''
        
        @app.errorhandler(404)
        def not_found_error(error):
            return render_template('errors/404.html'), 404
        
        @app.errorhandler(500)
        def internal_error(error):
            return render_template('errors/500.html'), 500
        
        @app.errorhandler(403)
        def forbidden_error(error):
            return render_template('errors/403.html'), 403
        
        @app.errorhandler(401)
        def unauthorized_error(error):
            return render_template('errors/401.html'), 401
    """
)
