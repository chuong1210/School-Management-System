from functools import wraps
from flask import jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import redis
from models import User, UserType

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
                return jsonify({'message': 'Token has been revoked'}), 401
            
            # Get current user
            current_user_id = get_jwt_identity()
            current_user = User.query.get(current_user_id)
            
            if not current_user:
                return jsonify({'message': 'User not found'}), 404
                
            return f(current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'message': 'Token validation failed', 'error': str(e)}), 401
    
    return decorated

def role_required(*allowed_roles):
    """Decorator to require specific user roles"""
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(current_user, *args, **kwargs):
            if current_user.user_type not in allowed_roles:
                return jsonify({
                    'message': 'Insufficient permissions',
                    'required_roles': allowed_roles,
                    'current_role': current_user.user_type
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