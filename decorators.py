from functools import wraps
from flask import jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime
import redis
from models import User, UserType, Department

# Redis client for token blacklist
redis_client = None

def init_redis(app):
    global redis_client
    redis_client = redis.from_url(app.config['REDIS_URL'])

def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        try:
            # Check if token is blacklisted
            jti = get_jwt()['jti']
            if redis_client.get(f"blacklist:{jti}"):
                return jsonify({
                    'error': 'TOKEN_REVOKED',
                    'message': 'Token đã bị thu hồi. Vui lòng đăng nhập lại.',
                    'details': {
                        'reason': 'Token has been blacklisted (logged out)',
                        'action_required': 'Please login again to get a new token'
                    },
                    'timestamp': datetime.utcnow().isoformat(),
                    'status_code': 401
                }), 401
            
            # Get current user
            current_user_id = get_jwt_identity()
            current_user = User.query.get(current_user_id)
            
            if not current_user:
                return jsonify({
                    'error': 'USER_NOT_FOUND',
                    'message': 'Người dùng không tồn tại trong hệ thống.',
                    'details': {
                        'user_id': current_user_id,
                        'reason': 'User account may have been deleted',
                        'action_required': 'Please contact administrator'
                    },
                    'timestamp': datetime.utcnow().isoformat(),
                    'status_code': 404
                }), 404
                
            return f(current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({
                'error': 'TOKEN_VALIDATION_FAILED',
                'message': 'Xác thực token thất bại.',
                'details': {
                    'reason': str(e),
                    'token_status': 'invalid_or_expired',
                    'action_required': 'Please login again to get a new token'
                },
                'timestamp': datetime.utcnow().isoformat(),
                'status_code': 401
            }), 401
    
    return decorated

def role_required(*allowed_roles):
    """Decorator to require specific user roles"""
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(current_user, *args, **kwargs):
            if current_user.user_type not in allowed_roles:
                if current_user.teacher and current_user.teacher.department_id:
                    department = Department.query.get(current_user.teacher.department_id)
                    department_name = department.department_name 
                elif current_user.teacher:
                    department_name = current_user.teacher.department
        
                if current_user.student and current_user.student.department_id:
                    department = Department.query.get(current_user.student.department_id)
                    department_name = department.department_name 
                return jsonify({
                    'error': 'INSUFFICIENT_PERMISSIONS',
                    'message': f'Bạn không có quyền truy cập endpoint này. Cần quyền: {", ".join(allowed_roles)}',
                    'details': {
                        'current_user': {
                            'username': current_user.username,
                            'user_type': current_user.user_type,
                            'user_id': current_user.user_id,
                            'department':department_name,
                        },
                        'required_roles': list(allowed_roles),
                        'endpoint': f.__name__,
                        'access_denied_reason': f'User có quyền "{current_user.user_type}" nhưng endpoint yêu cầu một trong các quyền: {", ".join(allowed_roles)}'
                    },
                    'timestamp': datetime.utcnow().isoformat(),
                    'status_code': 403
                }), 403
            
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator

def student_required(f):
    """Decorator to require student role"""
    return role_required(UserType.STUDENT.value)(f)

def teacher_required(f):
    """Decorator to require teacher role"""
    return role_required(UserType.TEACHER.value)(f)

def manager_required(f):
    """Decorator to require manager role"""
    return role_required(UserType.MANAGER.value)(f)

def teacher_or_manager_required(f):
    """Decorator to require teacher or manager role"""
    return role_required(UserType.TEACHER.value, UserType.MANAGER.value)(f)

def blacklist_token(jti, expires_delta):
    """Add token to blacklist"""
    try:
        redis_client.setex(f"blacklist:{jti}", expires_delta, "true")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to blacklist token: {str(e)}")
        return False

def is_token_blacklisted(jti):
    """Check if token is blacklisted"""
    try:
        return redis_client.get(f"blacklist:{jti}") is not None
    except Exception:
        return False