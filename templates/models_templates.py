"""
모델 템플릿들
"""
from textwrap import dedent

MODELS_INIT = dedent(
    """
    from .user import User
    from .post import Post
    
    __all__ = ['User', 'Post']
    """
)

USER_MODEL = dedent(
    """
    from datetime import datetime
    from werkzeug.security import generate_password_hash, check_password_hash
    from flask_login import UserMixin
    from app.extensions import db
    
    
    class User(UserMixin, db.Model):
        '''사용자 모델'''
        __tablename__ = 'users'
        
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        email = db.Column(db.String(120), unique=True, nullable=False)
        password_hash = db.Column(db.String(255))
        is_active = db.Column(db.Boolean, default=True)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        # 관계
        posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete-orphan')
        
        def __repr__(self):
            return f'<User {self.username}>'
        
        def set_password(self, password):
            '''비밀번호를 해시화하여 설정'''
            self.password_hash = generate_password_hash(password)
        
        def check_password(self, password):
            '''비밀번호 확인'''
            return check_password_hash(self.password_hash, password)
        
        @property
        def is_authenticated(self):
            return True
        
        @property
        def is_anonymous(self):
            return False
    """
)

POST_MODEL = dedent(
    """
    from datetime import datetime
    from app.extensions import db
    
    
    class Post(db.Model):
        '''게시글 모델'''
        __tablename__ = 'posts'
        
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(200), nullable=False)
        content = db.Column(db.Text, nullable=False)
        filename = db.Column(db.String(255))  # 업로드된 파일명
        file_path = db.Column(db.String(500))  # 파일 경로
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        # 외래키
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
        
        def __repr__(self):
            return f'<Post {self.title}>'
        
        @property
        def has_file(self):
            '''파일이 첨부되어 있는지 확인'''
            return bool(self.filename and self.file_path)
    """
)
