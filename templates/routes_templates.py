"""
라우트 템플릿들
"""
from textwrap import dedent

ROUTES_INIT = dedent(
    """
    from flask import Blueprint
    
    from .auth import auth_bp
    from .posts import posts_bp
    from .files import files_bp
    from .main import main_bp
    
    def init_app(app):
        '''블루프린트 등록'''
        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp, url_prefix='/auth')
        app.register_blueprint(posts_bp, url_prefix='/posts')
        app.register_blueprint(files_bp, url_prefix='/files')
    """
)

AUTH_ROUTES = dedent(
    """
    from flask import Blueprint, render_template, redirect, url_for, flash, request
    from flask_login import login_user, logout_user, login_required, current_user
    from urllib.parse import urlparse
    from app.extensions import db
    from app.models.user import User
    
    auth_bp = Blueprint('auth', __name__)
    
    @auth_bp.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('posts.list'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            remember = request.form.get('remember', False)
            
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user, remember=remember)
                next_page = request.args.get('next')
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('posts.list')
                return redirect(next_page)
            else:
                flash('잘못된 사용자명 또는 비밀번호입니다.', 'error')
        
        return render_template('auth/login.html')
    
    @auth_bp.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('로그아웃되었습니다.', 'info')
        return redirect(url_for('auth.login'))
    """
)

POSTS_ROUTES = dedent(
    """
    from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
    from flask_login import login_required, current_user
    from app.services.posts_service import PostsService
    from app.utils.pagination import Pagination
    
    posts_bp = Blueprint('posts', __name__)
    
    @posts_bp.route('/')
    def list():
        '''게시글 목록'''
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config.get('POSTS_PER_PAGE', 10)
        
        try:
            pagination = PostsService.get_posts(page=page, per_page=per_page)
        except Exception as e:
            flash('게시글을 불러오는 중 오류가 발생했습니다.', 'error')
            pagination = None
        
        return render_template('posts/list.html', pagination=pagination)
    
    @posts_bp.route('/new', methods=['GET', 'POST'])
    @login_required
    def new():
        '''게시글 작성'''
        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')
            file = request.files.get('file')
            
            if not title or not content:
                flash('제목과 내용을 입력해주세요.', 'error')
                return render_template('posts/form.html')
            
            try:
                PostsService.create_post(
                    title=title,
                    content=content,
                    user_id=current_user.id,
                    file=file
                )
                flash('게시글이 작성되었습니다.', 'success')
                return redirect(url_for('posts.list'))
            except Exception as e:
                flash('게시글 작성 중 오류가 발생했습니다.', 'error')
        
        return render_template('posts/form.html')
    
    @posts_bp.route('/<int:post_id>')
    def detail(post_id):
        '''게시글 상세'''
        try:
            post = PostsService.get_post(post_id)
        except Exception as e:
            flash('게시글을 찾을 수 없습니다.', 'error')
            return redirect(url_for('posts.list'))
        
        return render_template('posts/detail.html', post=post)
    
    @posts_bp.route('/<int:post_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit(post_id):
        '''게시글 수정'''
        try:
            post = PostsService.get_post(post_id)
        except Exception as e:
            flash('게시글을 찾을 수 없습니다.', 'error')
            return redirect(url_for('posts.list'))
        
        if post.user_id != current_user.id:
            flash('게시글을 수정할 권한이 없습니다.', 'error')
            return redirect(url_for('posts.detail', post_id=post_id))
        
        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')
            file = request.files.get('file')
            
            if not title or not content:
                flash('제목과 내용을 입력해주세요.', 'error')
                return render_template('posts/form.html', post=post)
            
            try:
                PostsService.update_post(
                    post_id=post_id,
                    title=title,
                    content=content,
                    user_id=current_user.id,
                    file=file
                )
                flash('게시글이 수정되었습니다.', 'success')
                return redirect(url_for('posts.detail', post_id=post_id))
            except Exception as e:
                flash('게시글 수정 중 오류가 발생했습니다.', 'error')
        
        return render_template('posts/form.html', post=post)
    
    @posts_bp.route('/<int:post_id>/delete', methods=['POST'])
    @login_required
    def delete(post_id):
        '''게시글 삭제'''
        try:
            PostsService.delete_post(post_id, current_user.id)
            flash('게시글이 삭제되었습니다.', 'success')
        except PermissionError:
            flash('게시글을 삭제할 권한이 없습니다.', 'error')
        except Exception as e:
            flash('게시글 삭제 중 오류가 발생했습니다.', 'error')
        
        return redirect(url_for('posts.list'))
    """
)

MAIN_ROUTES = dedent(
    """
    from flask import Blueprint, redirect, url_for, render_template
    
    main_bp = Blueprint('main', __name__)
    
    @main_bp.route('/')
    def index():
        '''메인 페이지'''
        return render_template('index.html')
    """
)

FILES_ROUTES = dedent(
    """
    import os
    from flask import Blueprint, send_file, abort, current_app
    from app.models.post import Post
    
    files_bp = Blueprint('files', __name__)
    
    @files_bp.route('/download/<int:post_id>')
    def download(post_id):
        '''파일 다운로드'''
        post = Post.query.get_or_404(post_id)
        
        if not post.has_file:
            abort(404)
        
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], post.file_path)
        
        if not os.path.exists(file_path):
            abort(404)
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=post.filename
        )
    """
)
