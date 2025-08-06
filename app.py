from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import os
from datetime import datetime
from config import config
from models import db
from routes import auth_bp, student_bp, teacher_bp, manager_bp
from decorators import init_redis
from flask_migrate import Migrate
from sqlalchemy.exc import OperationalError
import time

def create_app(config_name=None):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    with app.app_context():
        retries = 5
        for i in range(retries):
            try:
                db.create_all()
                break
            except OperationalError:
                print(f"Database unavailable, retrying in 3s... ({i+1}/{retries})")
                time.sleep(3)
    migrate = Migrate(app, db)  # Initialize Flask-Migrate
    jwt = JWTManager(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Initialize Redis for token blacklist
    init_redis(app)
    
    # JWT Error Handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': 'TOKEN_EXPIRED',
            'message': 'Token đã hết hạn. Vui lòng đăng nhập lại hoặc làm mới token.',
            'details': {
                'expired_at': datetime.fromtimestamp(jwt_payload['exp']).isoformat(),
                'token_type': jwt_payload.get('type', 'access'),
                'action_required': 'Use refresh token to get new access token or login again'
            },
            'timestamp': datetime.utcnow().isoformat(),
            'status_code': 401
        }), 401

    # @jwt.invalid_token_loader
    # def invalid_token_callback(error):
    #     return jsonify({
    #         'error': 'INVALID_TOKEN',
    #         'message': 'Token không hợp lệ.',
    #         'details': {
    #             'reason': str(error),
    #             'action_required': 'Please provide a valid JWT token'
    #         },
    #         'timestamp': datetime.utcnow().isoformat(),
    #         'status_code': 401
    #     }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'error': 'TOKEN_REQUIRED',
            'message': 'Yêu cầu token xác thực để truy cập endpoint này.',
            'details': {
                'reason': 'Authorization header is missing or malformed',
                'expected_format': 'Authorization: Bearer <your_jwt_token>',
                'action_required': 'Please login to get an access token'
            },
            'timestamp': datetime.utcnow().isoformat(),
            'status_code': 401
        }), 401

    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': 'FRESH_TOKEN_REQUIRED',
            'message': 'Endpoint này yêu cầu token fresh (mới đăng nhập).',
            'details': {
                'reason': 'This endpoint requires a fresh token for security',
                'action_required': 'Please login again to get a fresh token'
            },
            'timestamp': datetime.utcnow().isoformat(),
            'status_code': 401
        }), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': 'TOKEN_REVOKED',
            'message': 'Token đã bị thu hồi.',
            'details': {
                'reason': 'Token has been revoked (user logged out)',
                'action_required': 'Please login again to get a new token'
            },
            'timestamp': datetime.utcnow().isoformat(),
            'status_code': 401
        }), 401

    # Global Error Handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'error': 'BAD_REQUEST',
            'message': 'Yêu cầu không hợp lệ.',
            'details': {
                'reason': str(error.description) if hasattr(error, 'description') else 'Invalid request format or missing required fields',
                'status_code': 400
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'NOT_FOUND',
            'message': 'Endpoint không tồn tại.',
            'details': {
                'reason': 'The requested endpoint was not found on this server',
                'available_endpoints': {
                    'auth': '/api/auth',
                    'student': '/api/student', 
                    'teacher': '/api/teacher',
                    'manager': '/api/manager'
                },
                'status_code': 404
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'error': 'METHOD_NOT_ALLOWED',
            'message': 'Phương thức HTTP không được phép.',
            'details': {
                'reason': f'Method {error.description} is not allowed for this endpoint',
                'allowed_methods': list(error.valid_methods) if hasattr(error, 'valid_methods') else [],
                'status_code': 405
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 405

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': 'Lỗi máy chủ nội bộ.',
            'details': {
                'reason': 'An unexpected error occurred on the server',
                'action_required': 'Please try again later or contact administrator',
                'status_code': 500
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 500
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(student_bp, url_prefix='/api/student')
    app.register_blueprint(teacher_bp, url_prefix='/api/teacher')
    app.register_blueprint(manager_bp, url_prefix='/api/manager')
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {
            'status': 'healthy', 
            'message': 'School Management API is running',
            'timestamp': datetime.utcnow().isoformat()
        }, 200
    
    # Root endpoint
    @app.route('/')
    def index():
        return {
            'message': 'School Management System API',
            'version': '1.0.0',
            'endpoints': {
                'auth': '/api/auth',
                'student': '/api/student',
                'teacher': '/api/teacher',
                'manager': '/api/manager'
            },
            'timestamp': datetime.utcnow().isoformat()
        }, 200
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)