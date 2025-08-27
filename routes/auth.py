from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from datetime import datetime
from models import db, User, Student, Teacher, Department, UserType
from decorators import token_required, blacklist_token

# Import helpers từ file helpers.py
from .helpers import error_response, success_response

auth_bp = Blueprint('auth', __name__)

# ====================== AUTH ROUTES ======================

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Required fields validation
        required_fields = ['username', 'password', 'full_name', 'user_type']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return error_response(
                'MISSING_REQUIRED_FIELDS',
                'Thiếu các trường bắt buộc.',
                {'missing_fields': missing_fields, 'required_fields': required_fields}
            )
        
        # Check if username already exists
        if User.query.filter_by(username=data['username']).first():
            return error_response(
                'USERNAME_EXISTS',
                'Tên đăng nhập đã tồn tại.',
                {'username': data['username'], 'suggestion': 'Please choose a different username'},
                409
            )
        
        # Check if email already exists (if provided)
        if data.get('email') and User.query.filter_by(email=data['email']).first():
            return error_response(
                'EMAIL_EXISTS', 
                'Email đã được sử dụng.',
                {'email': data['email']},
                409
            )
        
        # Validate user type
        valid_user_types = [e.value for e in UserType]
        if data['user_type'] not in valid_user_types:
            return error_response(
                'INVALID_USER_TYPE',
                'Loại người dùng không hợp lệ.',
                {'provided_type': data['user_type'], 'valid_types': valid_user_types}
            )
        
        # Create new user
        user = User(
            username=data['username'],
            full_name=data['full_name'],
            email=data.get('email'),
            phone_number=data.get('phone_number'),
            user_type=data['user_type']
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Create specific user type record
        if data['user_type'] == UserType.STUDENT.value:
            # Validate department for student
            department_id = data.get('department_id')
            if department_id:
                department = Department.query.get(department_id)
                if not department:
                    return error_response(
                        'DEPARTMENT_NOT_FOUND',
                        'Khoa không tồn tại.',
                        {'department_id': department_id}
                    )
            
            student = Student(
                user_id=user.user_id,
                student_code=data.get('student_code'),
                date_of_birth=datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date() if data.get('date_of_birth') else None,
                major=data.get('major'),
                enrollment_date=datetime.strptime(data['enrollment_date'], '%Y-%m-%d').date() if data.get('enrollment_date') else None,
                department_id=department_id
            )
            db.session.add(student)
            
        elif data['user_type'] == UserType.TEACHER.value:
            # Validate department for teacher
            department_id = data.get('department_id')
            if department_id:
                department = Department.query.get(department_id)
                if not department:
                    return error_response(
                        'DEPARTMENT_NOT_FOUND',
                        'Khoa không tồn tại.',
                        {'department_id': department_id}
                    )
            
            teacher = Teacher(
                user_id=user.user_id,
                teacher_code=data.get('teacher_code'),
                department=data.get('department'),  # Keep for backward compatibility
                hire_date=datetime.strptime(data['hire_date'], '%Y-%m-%d').date() if data.get('hire_date') else None,
                department_id=department_id
            )
            db.session.add(teacher)
        
        db.session.commit()
        
        return success_response(
            'Đăng ký tài khoản thành công.',
            {'user': user.to_dict()},
            201
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(
            'REGISTRATION_FAILED',
            'Đăng ký thất bại.',
            {'error_details': str(e)},
            500
        )

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        
        if not data.get('username') or not data.get('password'):
            return error_response(
                'MISSING_CREDENTIALS',
                'Tên đăng nhập và mật khẩu là bắt buộc.',
                {'required_fields': ['username', 'password']}
            )
        
        user = User.query.filter_by(username=data['username']).first()
        
        if not user or not user.check_password(data['password']):
            return error_response(
                'INVALID_CREDENTIALS',
                'Tên đăng nhập hoặc mật khẩu không đúng.',
                {'username': data['username']},
                401
            )
        
        # Update last login
        user.update_last_login()
        
        # Get department info for claims
        department_name = None
        if user.teacher and user.teacher.department_id:
            department = Department.query.get(user.teacher.department_id)
            department_name = department.department_name if department else user.teacher.department
        elif user.teacher:
            department_name = user.teacher.department
        
        claims = {
            'username': user.username,
            'user_type': user.user_type,
            'full_name': user.full_name,
            'department': department_name,
        }
        
        access_token = create_access_token(identity=str(user.user_id), additional_claims=claims)
        refresh_token = create_refresh_token(identity=str(user.user_id))
        
        # Get user-specific data
        user_data = user.to_dict()
        if user.user_type == UserType.STUDENT.value and user.student:
            user_data['student_info'] = user.student.to_dict()
            if user.student.department_id:
                department = Department.query.get(user.student.department_id)
                user_data['department_info'] = department.to_dict() if department else None
        elif user.user_type == UserType.TEACHER.value and user.teacher:
            user_data['teacher_info'] = user.teacher.to_dict()
            if user.teacher.department_id:
                department = Department.query.get(user.teacher.department_id)
                user_data['department_info'] = department.to_dict() if department else None
        
        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user_data
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Login failed', 'error': str(e)}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        # Get department info for claims
        department_name = None
        if user.teacher and user.teacher.department_id:
            department = Department.query.get(user.teacher.department_id)
            department_name = department.department_name if department else user.teacher.department
        elif user.teacher:
            department_name = user.teacher.department
        
        new_access_token = create_access_token(
            identity=current_user_id,
            additional_claims={
                'username': user.username,
                'user_type': user.user_type,
                'full_name': user.full_name,
                'department': department_name,
            }
        )
        
        return jsonify({
            'access_token': new_access_token
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Token refresh failed', 'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """User logout"""
    try:
        jti = get_jwt()['jti']
        expires_delta = current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
        
        if blacklist_token(jti, int(expires_delta.total_seconds())):
            return jsonify({'message': 'Successfully logged out'}), 200
        else:
            return jsonify({'message': 'Logout failed'}), 500
            
    except Exception as e:
        return jsonify({'message': 'Logout failed', 'error': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """Get current user profile"""
    try:
        user_data = current_user.to_dict()
        
        # Add specific info based on user type
        if current_user.user_type == UserType.STUDENT.value and current_user.student:
            user_data['student_info'] = current_user.student.to_dict()
            if current_user.student.department_id:
                department = Department.query.get(current_user.student.department_id)
                user_data['department_info'] = department.to_dict() if department else None
        elif current_user.user_type == UserType.TEACHER.value and current_user.teacher:
            user_data['teacher_info'] = current_user.teacher.to_dict()
            if current_user.teacher.department_id:
                department = Department.query.get(current_user.teacher.department_id)
                user_data['department_info'] = department.to_dict() if department else None
        
        return jsonify({
            'user': user_data
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to get profile', 'error': str(e)}), 500