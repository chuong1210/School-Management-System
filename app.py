from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import os
from config import config
from models import db
from routes import auth_bp, student_bp, teacher_bp, manager_bp
from decorators import init_redis

def create_app(config_name=None):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    jwt = JWTManager(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Initialize Redis for token blacklist
    init_redis(app)
    
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
        return {'status': 'healthy', 'message': 'School Management API is running'}, 200
    
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
            }
        }, 200
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)