"""
서비스 레이어 템플릿들
"""
from textwrap import dedent
import os

POSTS_SERVICE = dedent(
    """
    from flask import current_app
    from app.extensions import db, cache
    from app.models.post import Post
    from app.utils.storage import save_upload, delete_upload
    
    
    class PostsService:
        '''게시글 서비스 클래스'''
        
        @staticmethod
        def get_posts(page=1, per_page=10):
            '''게시글 목록 조회'''
            return Post.query.order_by(Post.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
        
        @staticmethod
        def get_post(post_id):
            '''게시글 상세 조회'''
            return Post.query.get_or_404(post_id)
        
        @staticmethod
        def create_post(title, content, user_id, file=None):
            '''게시글 생성'''
            post = Post(
                title=title,
                content=content,
                user_id=user_id
            )
            
            # 파일 업로드 처리
            if file:
                upload_result = save_upload(file, subfolder='posts')
                if upload_result:
                    post.filename = upload_result['filename']
                    post.file_path = upload_result['relative_path']
            
            db.session.add(post)
            db.session.commit()
            
            # 캐시 무효화 (필요시)
            pass
            
            return post
        
        @staticmethod
        def update_post(post_id, title, content, user_id, file=None):
            '''게시글 수정'''
            post = Post.query.get_or_404(post_id)
            
            # 권한 확인
            if post.user_id != user_id:
                raise PermissionError("게시글을 수정할 권한이 없습니다.")
            
            post.title = title
            post.content = content
            
            # 파일 업로드 처리
            if file:
                # 기존 파일 삭제
                if post.file_path:
                    old_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], post.file_path)
                    delete_upload(old_file_path)
                
                # 새 파일 저장
                upload_result = save_upload(file, subfolder='posts')
                if upload_result:
                    post.filename = upload_result['filename']
                    post.file_path = upload_result['relative_path']
            
            db.session.commit()
            
            # 캐시 무효화 (필요시)
            pass
            
            return post
        
        @staticmethod
        def delete_post(post_id, user_id):
            '''게시글 삭제'''
            post = Post.query.get_or_404(post_id)
            
            # 권한 확인
            if post.user_id != user_id:
                raise PermissionError("게시글을 삭제할 권한이 없습니다.")
            
            # 첨부 파일 삭제
            if post.file_path:
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], post.file_path)
                delete_upload(file_path)
            
            db.session.delete(post)
            db.session.commit()
            
            # 캐시 무효화 (필요시)
            pass
            
            return True
    """
)
