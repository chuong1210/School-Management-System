from flask import Blueprint, request, jsonify, current_app, make_response
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, 
    get_jwt_identity, get_jwt
)
from datetime import datetime, timedelta
from models import (
    db, User, Student, Teacher, Course, Class, Schedule, Department,
    Enrollment, UserType, ClassStatus, EnrollmentStatus
)
from decorators import (
    token_required, student_required, teacher_required, 
    manager_required, teacher_or_manager_required, blacklist_token
)

# Create Blueprint
auth_bp = Blueprint('auth', __name__)
student_bp = Blueprint('student', __name__)
teacher_bp = Blueprint('teacher', __name__)
manager_bp = Blueprint('manager', __name__)

# Helper function for error responses
def error_response(error_code, message, details=None, status_code=400):
    """Standardized error response format"""
    response_data = {
        'error': error_code,
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
        'status_code': status_code
    }
    if details:
        response_data['details'] = details

    response = make_response(jsonify(response_data), status_code)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

# Helper function for success responses
def success_response(message, data=None, status_code=200):
    """Standardized success response format"""
    response_data = {
        'success': True,
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
        'status_code': status_code
    }
    if data:
        response_data['data'] = data

    response = make_response(jsonify(response_data), status_code)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

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

# ====================== STUDENT ROUTES ======================

@student_bp.route('/notifications', methods=['GET'])
@student_required
def get_student_notifications(current_user):
    """Get notifications for students"""
    try:
        # Mock notifications - in real app, fetch from database
        notifications = [
            {
                'id': 1,
                'title': 'Thông báo lịch thi cuối kỳ',
                'content': 'Lịch thi cuối kỳ học kỳ 1 năm học 2024-2025 đã được cập nhật',
                'date': '2024-12-01',
                'type': 'exam'
            },
            {
                'id': 2,
                'title': 'Thông báo nghỉ lễ',
                'content': 'Trường nghỉ lễ Quốc khánh từ ngày 2/9 đến 4/9',
                'date': '2024-08-30',
                'type': 'holiday'
            }
        ]
        
        return jsonify({
            'notifications': notifications
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to get notifications', 'error': str(e)}), 500

@student_bp.route('/schedule', methods=['GET'])
@student_required
def get_student_schedule(current_user):
    """Get student's class schedule"""
    try:
        if not current_user.student:
            return jsonify({'message': 'Student profile not found'}), 404
        
        # Get student's enrolled classes with schedules
        enrollments = Enrollment.query.filter_by(
            student_id=current_user.student.student_id,
            status=EnrollmentStatus.REGISTERED.value
        ).all()
        
        schedule_data = []
        for enrollment in enrollments:
            class_obj = enrollment.class_ref
            course = class_obj.course
            schedules = class_obj.schedules
            
            for schedule in schedules:
                schedule_data.append({
                    'class_id': class_obj.class_id,
                    'course_code': course.course_code,
                    'course_name': course.course_name,
                    'credits': course.credits,
                    'day_of_week': schedule.day_of_week,
                    'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
                    'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
                    'room_location': schedule.room_location,
                    'semester': class_obj.semester,
                    'academic_year': class_obj.academic_year
                })
        
        return jsonify({
            'schedule': schedule_data
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to get schedule', 'error': str(e)}), 500

@student_bp.route('/enroll', methods=['POST'])
@student_required
def enroll_course(current_user):
    """Enroll in a course - only allow same department"""
    try:
        data = request.get_json()
        
        if not data.get('class_id'):
            return error_response('MISSING_CLASS_ID', 'Yêu cầu cung cấp class_id.')
        
        if not current_user.student:
            return error_response('STUDENT_NOT_FOUND', 'Hồ sơ sinh viên không tồn tại.', status_code=404)
        
        class_obj = Class.query.get(data['class_id'])
        if not class_obj:
            return error_response('CLASS_NOT_FOUND', 'Lớp học không tồn tại.', status_code=404)
        
        if class_obj.status != ClassStatus.OPEN.value:
            return error_response('CLASS_NOT_OPEN', 'Lớp học không mở để đăng ký.')
        
        if class_obj.current_enrollment >= class_obj.max_capacity:
            return error_response('CLASS_FULL', 'Lớp học đã đầy.')
        
        # Check department match - student can only enroll in courses from their department
        if current_user.student.department_id and class_obj.course.department_id:
            if current_user.student.department_id != class_obj.course.department_id:
                student_dept = Department.query.get(current_user.student.department_id)
                course_dept = Department.query.get(class_obj.course.department_id)
                return error_response(
                    'DEPARTMENT_MISMATCH',
                    'Bạn chỉ có thể đăng ký các lớp học thuộc chuyên ngành của mình.',
                    {
                        'student_department': student_dept.department_name if student_dept else None,
                        'course_department': course_dept.department_name if course_dept else None
                    }
                )
        
        # Check if already enrolled
        existing_enrollment = Enrollment.query.filter_by(
            student_id=current_user.student.student_id,
            class_id=data['class_id']
        ).first()
        
        if existing_enrollment:
            if existing_enrollment.status == EnrollmentStatus.REGISTERED.value:
                return error_response('ALREADY_ENROLLED', 'Bạn đã đăng ký lớp học này.', status_code=409)
            else:
                # Re-enroll if previously cancelled
                existing_enrollment.status = EnrollmentStatus.REGISTERED.value
                existing_enrollment.enrollment_date = datetime.utcnow()
        else:
            # Create new enrollment
            enrollment = Enrollment(
                student_id=current_user.student.student_id,
                class_id=data['class_id'],
                status=EnrollmentStatus.REGISTERED.value
            )
            db.session.add(enrollment)
        
        # Update class enrollment count
        class_obj.current_enrollment += 1
        db.session.commit()
        
        return success_response(
            'Đăng ký lớp học thành công.',
            {
                'class_info': {
                    'class_id': class_obj.class_id,
                    'course_name': class_obj.course.course_name,
                    'course_code': class_obj.course.course_code,
                    'semester': class_obj.semester,
                    'academic_year': class_obj.academic_year
                }
            }
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(
            'ENROLL_FAILED',
            'Đăng ký lớp học thất bại.',
            {'error_details': str(e)},
            500
        )

@student_bp.route('/cancel-enrollment', methods=['POST'])
@student_required
def cancel_enrollment(current_user):
    """Cancel enrollment in a course"""
    try:
        data = request.get_json()
        
        if not data.get('class_id'):
            return error_response('MISSING_CLASS_ID', 'Yêu cầu cung cấp class_id.')
        
        if not current_user.student:
            return error_response('STUDENT_NOT_FOUND', 'Hồ sơ sinh viên không tồn tại.', status_code=404)
        
        # Verify class exists
        class_obj = Class.query.get(data['class_id'])
        if not class_obj:
            return error_response('CLASS_NOT_FOUND', 'Lớp học không tồn tại.', status_code=404)
        
        # Check if class is open
        if class_obj.status != ClassStatus.OPEN.value:
            return error_response(
                'CLASS_NOT_OPEN',
                'Không thể hủy đăng ký vì lớp học không ở trạng thái mở.',
                {'class_status': class_obj.status}
            )
        
        # Check if student is enrolled
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.student.student_id,
            class_id=data['class_id'],
            status=EnrollmentStatus.REGISTERED.value
        ).first()
        
        if not enrollment:
            return error_response(
                'NOT_ENROLLED',
                'Bạn chưa đăng ký lớp học này hoặc đăng ký đã bị hủy.',
                {'class_id': data['class_id']}
            )
        
        # Check cancellation period (within 14 days from class start date)
        current_date = datetime.utcnow().date()
        cancellation_deadline = class_obj.start_date + timedelta(days=14)
        if current_date > cancellation_deadline:
            return error_response(
                'OUTSIDE_CANCELLATION_PERIOD',
                'Không thể hủy đăng ký vì đã quá thời hạn hủy (14 ngày sau ngày bắt đầu).',
                {
                    'current_date': current_date.isoformat(),
                    'cancellation_deadline': cancellation_deadline.isoformat(),
                    'start_date': class_obj.start_date.isoformat()
                }
            )
        
        # Ensure no grade has been assigned
        if enrollment.grade is not None:
            return error_response(
                'GRADE_ASSIGNED',
                'Không thể hủy đăng ký vì điểm đã được ghi nhận.',
                {'class_id': data['class_id']}
            )
        
        # Update enrollment status and record cancellation time
        enrollment.status = EnrollmentStatus.CANCELLED.value
        enrollment.cancellation_date = datetime.utcnow()
        
        # Decrement class enrollment count
        class_obj.current_enrollment = max(0, class_obj.current_enrollment - 1)
        
        db.session.commit()
        
        return success_response(
            'Hủy đăng ký lớp học thành công.',
            {
                'class_info': {
                    'class_id': class_obj.class_id,
                    'course_name': class_obj.course.course_name,
                    'course_code': class_obj.course.course_code,
                    'semester': class_obj.semester,
                    'academic_year': class_obj.academic_year
                }
            }
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(
            'CANCEL_ENROLLMENT_FAILED',
            'Hủy đăng ký lớp học thất bại.',
            {'error_details': str(e)},
            500
        )

@student_bp.route('/available-classes', methods=['GET'])
@student_required
def get_available_classes(current_user):
    """Get available classes for enrollment - only from same department"""
    try:
        if not current_user.student:
            return error_response('STUDENT_NOT_FOUND', 'Hồ sơ sinh viên không tồn tại.', status_code=404)
        
        # Base query for open classes with available capacity
        query = Class.query.join(Course).filter(
            Class.status == ClassStatus.OPEN.value,
            Class.current_enrollment < Class.max_capacity
        )
        
        # Filter by student's department if available
        if current_user.student.department_id:
            query = query.filter(Course.department_id == current_user.student.department_id)
        
        available_classes = query.all()
        
        classes_data = []
        for class_obj in available_classes:
            # Check if student is already enrolled
            enrolled = Enrollment.query.filter_by(
                student_id=current_user.student.student_id,
                class_id=class_obj.class_id,
                status=EnrollmentStatus.REGISTERED.value
            ).first()
            
            if not enrolled:
                class_data = class_obj.to_dict()
                class_data['course_info'] = class_obj.course.to_dict()
                
                # Add department info
                if class_obj.course.department_id:
                    department = Department.query.get(class_obj.course.department_id)
                    class_data['department_info'] = department.to_dict() if department else None
                
                if class_obj.teacher:
                    class_data['teacher_info'] = {
                        'teacher_name': class_obj.teacher.user.full_name,
                        'department': class_obj.teacher.department
                    }
                classes_data.append(class_data)
        
        return jsonify({
            'available_classes': classes_data
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to get available classes', 'error': str(e)}), 500

# ====================== TEACHER ROUTES ======================

@teacher_bp.route('/teaching-schedule', methods=['GET'])
@teacher_required
def get_teaching_schedule(current_user):
    """Get teacher's teaching schedule"""
    try:
        if not current_user.teacher:
            return jsonify({'message': 'Teacher profile not found'}), 404
        
        # Get teacher's classes with schedules
        classes = Class.query.filter_by(teacher_id=current_user.teacher.teacher_id).all()
        
        schedule_data = []
        for class_obj in classes:
            course = class_obj.course
            schedules = class_obj.schedules
            
            for schedule in schedules:
                schedule_data.append({
                    'class_id': class_obj.class_id,
                    'course_code': course.course_code,
                    'course_name': course.course_name,
                    'credits': course.credits,
                    'day_of_week': schedule.day_of_week,
                    'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
                    'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
                    'room_location': schedule.room_location,
                    'semester': class_obj.semester,
                    'academic_year': class_obj.academic_year,
                    'current_enrollment': class_obj.current_enrollment,
                    'max_capacity': class_obj.max_capacity
                })
        
        return jsonify({
            'teaching_schedule': schedule_data
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to get teaching schedule', 'error': str(e)}), 500

@teacher_bp.route('/students', methods=['GET'])
@teacher_required
def get_teacher_students(current_user):
    """Get students in teacher's classes"""
    try:
        if not current_user.teacher:
            return jsonify({'message': 'Teacher profile not found'}), 404
        
        # Get all students enrolled in teacher's classes
        classes = Class.query.filter_by(teacher_id=current_user.teacher.teacher_id).all()
        
        students_data = []
        for class_obj in classes:
            enrollments = Enrollment.query.filter_by(
                class_id=class_obj.class_id,
                status=EnrollmentStatus.REGISTERED.value
            ).all()
            
            for enrollment in enrollments:
                student = enrollment.student
                student_data = {
                    'student_id': student.student_id,
                    'student_code': student.student_code,
                    'full_name': student.user.full_name,
                    'email': student.user.email,
                    'phone_number': student.user.phone_number,
                    'major': student.major,
                    'class_info': {
                        'class_id': class_obj.class_id,
                        'course_code': class_obj.course.course_code,
                        'course_name': class_obj.course.course_name,
                        'semester': class_obj.semester,
                        'academic_year': class_obj.academic_year
                    },
                    'grade': enrollment.grade
                }
                
                # Add department info
                if student.department_id:
                    department = Department.query.get(student.department_id)
                    student_data['department_info'] = department.to_dict() if department else None
                
                students_data.append(student_data)
        
        return jsonify({
            'students': students_data
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to get students', 'error': str(e)}), 500

@teacher_bp.route('/courses', methods=['GET'])
@teacher_required
def get_teacher_courses(current_user):
    """Get courses assigned to teacher"""
    try:
        if not current_user.teacher:
            return jsonify({'message': 'Teacher profile not found'}), 404
        
        # Get teacher's classes and their courses
        classes = Class.query.filter_by(teacher_id=current_user.teacher.teacher_id).all()
        
        courses_data = []
        course_ids = set()
        
        for class_obj in classes:
            if class_obj.course_id not in course_ids:
                course_ids.add(class_obj.course_id)
                course_data = class_obj.course.to_dict()
                
                # Add department info
                if class_obj.course.department_id:
                    department = Department.query.get(class_obj.course.department_id)
                    course_data['department_info'] = department.to_dict() if department else None
                
                # Add class information
                course_classes = [c for c in classes if c.course_id == class_obj.course_id]
                course_data['classes'] = [
                    {
                        'class_id': c.class_id,
                        'semester': c.semester,
                        'academic_year': c.academic_year,
                        'current_enrollment': c.current_enrollment,
                        'max_capacity': c.max_capacity,
                        'status': c.status
                    } for c in course_classes
                ]
                
                courses_data.append(course_data)
        
        return jsonify({
            'courses': courses_data
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to get courses', 'error': str(e)}), 500

# ====================== MANAGER ROUTES ======================

@manager_bp.route('/overview', methods=['GET'])
@manager_required
def get_system_overview(current_user):
    """Get system overview statistics"""
    try:
        # Get statistics
        total_students = Student.query.count()
        total_teachers = Teacher.query.count()
        total_courses = Course.query.count()
        total_classes = Class.query.count()
        active_classes = Class.query.filter_by(status=ClassStatus.OPEN.value).count()
        total_enrollments = Enrollment.query.filter_by(status=EnrollmentStatus.REGISTERED.value).count()
        total_departments = Department.query.count()
        
        return jsonify({
            'overview': {
                'total_students': total_students,
                'total_teachers': total_teachers,
                'total_courses': total_courses,
                'total_classes': total_classes,
                'active_classes': active_classes,
                'total_enrollments': total_enrollments,
                'total_departments': total_departments
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to get overview', 'error': str(e)}), 500

@manager_bp.route('/departments', methods=['GET'])
@manager_required
def get_all_departments(current_user):
    """Get all departments"""
    try:
        departments = Department.query.all()
        departments_data = [dept.to_dict() for dept in departments]
        
        return jsonify({
            'departments': departments_data
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to get departments', 'error': str(e)}), 500

@manager_bp.route('/create-class', methods=['POST'])
@manager_required
def create_class(current_user):
    """Create a new class with specified fields, without teacher assignment"""
    try:
        data = request.get_json()
        
        required_fields = ['course_id', 'semester', 'academic_year', 'max_capacity', 'start_date', 'end_date']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return error_response(
                'MISSING_REQUIRED_FIELDS',
                'Thiếu các trường bắt buộc.',
                {'missing_fields': missing_fields, 'required_fields': required_fields}
            )
        
        # Verify course exists
        course = Course.query.get(data['course_id'])
        if not course:
            return error_response('COURSE_NOT_FOUND', 'Khóa học không tồn tại.', status_code=404)
        
        # Validate dates
        try:
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            if start_date >= end_date:
                return error_response(
                    'INVALID_DATES',
                    'Ngày bắt đầu phải trước ngày kết thúc.',
                    {'start_date': data['start_date'], 'end_date': data['end_date']}
                )
        except ValueError:
            return error_response('INVALID_DATE_FORMAT', 'Định dạng ngày không hợp lệ (YYYY-MM-DD).')

        # Create new class
        new_class = Class(
            course_id=data['course_id'],
            semester=data['semester'],
            academic_year=data['academic_year'],
            max_capacity=data['max_capacity'],
            status=ClassStatus.OPEN.value,
            start_date=start_date,
            end_date=end_date
        )
        
        db.session.add(new_class)
        db.session.commit()
        
        class_data = new_class.to_dict()
        class_data['course_info'] = course.to_dict()
        
        # Add department info
        if course.department_id:
            department = Department.query.get(course.department_id)
            class_data['department_info'] = department.to_dict() if department else None
        
        return success_response(
            'Tạo lớp học thành công.',
            {'class': class_data},
            201
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(
            'CREATE_CLASS_FAILED',
            'Tạo lớp học thất bại.',
            {'error_details': str(e)},
            500
        )

@manager_bp.route('/assign-teacher', methods=['POST'])
@manager_required
def assign_teacher(current_user):
    """Assign teacher to a class - only allow same department"""
    try:
        data = request.get_json()
        
        if not data.get('class_id') or not data.get('teacher_id'):
            return error_response(
                'MISSING_REQUIRED_FIELDS',
                'class_id và teacher_id là bắt buộc.',
                {'required_fields': ['class_id', 'teacher_id']}
            )
        
        # Verify class exists
        class_obj = Class.query.get(data['class_id'])
        if not class_obj:
            return error_response('CLASS_NOT_FOUND', 'Lớp học không tồn tại.', status_code=404)
        
        # Verify teacher exists
        teacher = Teacher.query.get(data['teacher_id'])
        if not teacher:
            return error_response('TEACHER_NOT_FOUND', 'Giáo viên không tồn tại.', status_code=404)
        
        # Check department match - teacher can only teach courses from their department
        if teacher.department_id and class_obj.course.department_id:
            if teacher.department_id != class_obj.course.department_id:
                teacher_dept = Department.query.get(teacher.department_id)
                course_dept = Department.query.get(class_obj.course.department_id)
                return error_response(
                    'DEPARTMENT_MISMATCH',
                    'Giáo viên chỉ có thể dạy các lớp học thuộc chuyên ngành của mình.',
                    {
                        'teacher_department': teacher_dept.department_name if teacher_dept else None,
                        'course_department': course_dept.department_name if course_dept else None
                    }
                )
        
        # Assign teacher to class
        class_obj.teacher_id = data['teacher_id']
        db.session.commit()
        
        return success_response(
            'Phân công giáo viên thành công.',
            {
                'class_id': class_obj.class_id,
                'teacher_name': teacher.user.full_name,
                'course_name': class_obj.course.course_name
            }
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(
            'ASSIGN_TEACHER_FAILED',
            'Phân công giáo viên thất bại.',
            {'error_details': str(e)},
            500
        )

@manager_bp.route('/add-student', methods=['POST'])
@manager_required
def add_student(current_user):
    """Add a new student"""
    try:
        data = request.get_json()
        
        required_fields = ['username', 'password', 'full_name', 'email', 'phone_number', 'major', 'department_id']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return error_response(
                'MISSING_REQUIRED_FIELDS',
                'Thiếu các trường bắt buộc.',
                {'missing_fields': missing_fields, 'required_fields': required_fields}
            )
        
        # Check if username exists
        if User.query.filter_by(username=data['username']).first():
            return error_response(
                'USERNAME_EXISTS',
                'Tên đăng nhập đã tồn tại.',
                {'username': data['username']},
                409
            )
        
        # Check if email exists
        if User.query.filter_by(email=data['email']).first():
            return error_response(
                'EMAIL_EXISTS',
                'Email đã được sử dụng.',
                {'email': data['email']},
                409
            )
        
        # Verify department exists
        department = Department.query.get(data['department_id'])
        if not department:
            return error_response(
                'DEPARTMENT_NOT_FOUND',
                'Khoa không tồn tại.',
                {'department_id': data['department_id']},
                404
            )
        
        # Create user
        user = User(
            username=data['username'],
            full_name=data['full_name'],
            email=data['email'],
            phone_number=data['phone_number'],
            user_type=UserType.STUDENT.value
        )
        user.set_password(data['password'])
        db.session.add(user)
        db.session.flush()
        
        # Create student
        student = Student(
            user_id=user.user_id,
            major=data['major'],
            department_id=data['department_id'],
            student_code=data.get('student_code'),
            date_of_birth=datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date() if data.get('date_of_birth') else None,
            enrollment_date=datetime.strptime(data['enrollment_date'], '%Y-%m-%d').date() if data.get('enrollment_date') else None
        )
        db.session.add(student)
        db.session.commit()
        
        user_data = user.to_dict()
        user_data['student_info'] = student.to_dict()
        user_data['department_info'] = department.to_dict()
        
        return success_response(
            'Thêm sinh viên thành công.',
            {'user': user_data},
            201
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(
            'ADD_STUDENT_FAILED',
            'Thêm sinh viên thất bại.',
            {'error_details': str(e)},
            500
        )

@manager_bp.route('/add-teacher', methods=['POST'])
@manager_required
def add_teacher(current_user):
    """Add a new teacher"""
    try:
        data = request.get_json()
        
        required_fields = ['username', 'password', 'full_name', 'email', 'phone_number', 'department', 'department_id']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return error_response(
                'MISSING_REQUIRED_FIELDS',
                'Thiếu các trường bắt buộc.',
                {'missing_fields': missing_fields, 'required_fields': required_fields}
            )
        
        # Check if username exists
        if User.query.filter_by(username=data['username']).first():
            return error_response(
                'USERNAME_EXISTS',
                'Tên đăng nhập đã tồn tại.',
                {'username': data['username']},
                409
            )
        
        # Check if email exists
        if User.query.filter_by(email=data['email']).first():
            return error_response(
                'EMAIL_EXISTS',
                'Email đã được sử dụng.',
                {'email': data['email']},
                409
            )
        
        # Verify department exists
        department = Department.query.get(data['department_id'])
        if not department:
            return error_response(
                'DEPARTMENT_NOT_FOUND',
                'Khoa không tồn tại.',
                {'department_id': data['department_id']},
                404
            )
        
        # Create user
        user = User(
            username=data['username'],
            full_name=data['full_name'],
            email=data['email'],
            phone_number=data['phone_number'],
            user_type=UserType.TEACHER.value
        )
        user.set_password(data['password'])
        db.session.add(user)
        db.session.flush()
        
        # Create teacher
        teacher = Teacher(
            user_id=user.user_id,
            department=data['department'],
            department_id=data['department_id'],
            teacher_code=data.get('teacher_code'),
            hire_date=datetime.strptime(data['hire_date'], '%Y-%m-%d').date() if data.get('hire_date') else None
        )
        db.session.add(teacher)
        db.session.commit()
        
        user_data = user.to_dict()
        user_data['teacher_info'] = teacher.to_dict()
        user_data['department_info'] = department.to_dict()
        
        return success_response(
            'Thêm giáo viên thành công.',
            {'user': user_data},
            201
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(
            'ADD_TEACHER_FAILED',
            'Thêm giáo viên thất bại.',
            {'error_details': str(e)},
            500
        )

@manager_bp.route('/all-users', methods=['GET'])
@manager_required
def get_all_users(current_user):
    """Get all users in the system"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        user_type = request.args.get('user_type')
        department_id = request.args.get('department_id', type=int)
        
        query = User.query
        
        if user_type:
            query = query.filter_by(user_type=user_type)
        
        # Filter by department if specified
        if department_id:
            if user_type == UserType.STUDENT.value:
                query = query.join(Student).filter(Student.department_id == department_id)
            elif user_type == UserType.TEACHER.value:
                query = query.join(Teacher).filter(Teacher.department_id == department_id)
        
        users = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        users_data = []
        for user in users.items:
            user_data = user.to_dict()
            
            # Add specific info based on user type
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
            
            users_data.append(user_data)
        
        return jsonify({
            'users': users_data,
            'pagination': {
                'page': users.page,
                'pages': users.pages,
                'per_page': users.per_page,
                'total': users.total,
                'has_next': users.has_next,
                'has_prev': users.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to get users', 'error': str(e)}), 500

@manager_bp.route('/all-classes', methods=['GET'])
@manager_required
def get_all_classes(current_user):
    """Get all classes in the system"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        department_id = request.args.get('department_id', type=int)
        
        query = Class.query.join(Course)
        
        # Filter by department if specified
        if department_id:
            query = query.filter(Course.department_id == department_id)
        
        classes = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        classes_data = []
        for class_obj in classes.items:
            class_data = class_obj.to_dict()
            class_data['course_info'] = class_obj.course.to_dict()
            
            # Add department info
            if class_obj.course.department_id:
                department = Department.query.get(class_obj.course.department_id)
                class_data['department_info'] = department.to_dict() if department else None
            
            if class_obj.teacher:
                class_data['teacher_info'] = {
                    'teacher_name': class_obj.teacher.user.full_name,
                    'department': class_obj.teacher.department
                }
            
            classes_data.append(class_data)
        
        return jsonify({
            'classes': classes_data,
            'pagination': {
                'page': classes.page,
                'pages': classes.pages,
                'per_page': classes.per_page,  
                'total': classes.total,
                'has_next': classes.has_next,
                'has_prev': classes.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to get classes', 'error': str(e)}), 500

@manager_bp.route('/create-course', methods=['POST'])
@manager_required
def create_course(current_user):
    """Create a new course"""
    try:
        data = request.get_json()
        
        required_fields = ['course_code', 'course_name', 'credits', 'department_id']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return error_response(
                'MISSING_REQUIRED_FIELDS',
                'Thiếu các trường bắt buộc.',
                {'missing_fields': missing_fields, 'required_fields': required_fields}
            )
        
        # Check if course code exists
        if Course.query.filter_by(course_code=data['course_code']).first():
            return error_response(
                'COURSE_CODE_EXISTS',
                'Mã khóa học đã tồn tại.',
                {'course_code': data['course_code']},
                409
            )
        
        # Verify department exists
        department = Department.query.get(data['department_id'])
        if not department:
            return error_response(
                'DEPARTMENT_NOT_FOUND',
                'Khoa không tồn tại.',
                {'department_id': data['department_id']},
                404
            )
        
        # Create course
        course = Course(
            course_code=data['course_code'],
            course_name=data['course_name'],
            credits=data['credits'],
            description=data.get('description'),
            department_id=data['department_id']
        )
        
        db.session.add(course)
        db.session.commit()
        
        course_data = course.to_dict()
        course_data['department_info'] = department.to_dict()
        
        return success_response(
            'Tạo khóa học thành công.',
            {'course': course_data},
            201
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(
            'CREATE_COURSE_FAILED',
            'Tạo khóa học thất bại.',
            {'error_details': str(e)},
            500
        )