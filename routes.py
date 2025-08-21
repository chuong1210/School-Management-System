from flask import Blueprint, request, jsonify, current_app,make_response
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, 
    get_jwt_identity, get_jwt
)
from datetime import datetime, timedelta
from models import (
    db, User, Student, Teacher, Course, Class, Schedule, 
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
            student = Student(
                user_id=user.user_id,
                student_code=data.get('student_code'),
                date_of_birth=datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date() if data.get('date_of_birth') else None,
                major=data.get('major'),
                enrollment_date=datetime.strptime(data['enrollment_date'], '%Y-%m-%d').date() if data.get('enrollment_date') else None
            )
            db.session.add(student)
            
        elif data['user_type'] == UserType.TEACHER.value:
            teacher = Teacher(
                user_id=user.user_id,
                teacher_code=data.get('teacher_code'),
                department=data.get('department'),
                hire_date=datetime.strptime(data['hire_date'], '%Y-%m-%d').date() if data.get('hire_date') else None
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
        claims = {
        'username': user.username,
        'user_type': user.user_type,
        'full_name': user.full_name,
        'department': getattr(user.teacher, 'department', None),
        'major': getattr(user.student, 'major', None)
    }
        access_token = create_access_token(identity=str(user.user_id), additional_claims=claims)
        # Create tokens
        # access_token = create_access_token(
        #     identity=str(user.user_id),
        #     additional_claims={
        #         'username': user.username,
        #         'user_type': user.user_type,
        #         'full_name': user.full_name,
        #         'department': user.teacher.department if user.user_type == UserType.TEACHER.value else None,
        #         'major': user.student.major if user.user_type == UserType.STUDENT.value else None
        #     }
        # )
        refresh_token = create_refresh_token(identity=str(user.user_id))
        
        # Get user-specific data
        user_data = user.to_dict()
        if user.user_type == UserType.STUDENT.value and user.student:
            user_data['student_info'] = user.student.to_dict()
        elif user.user_type == UserType.TEACHER.value and user.teacher:
            user_data['teacher_info'] = user.teacher.to_dict()
        
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
        
        new_access_token = create_access_token(
            identity=current_user_id,
            additional_claims={
                'username': user.username,
                'user_type': user.user_type,
                'full_name': user.full_name,
                'department': getattr(user.teacher, 'department', None),
                'major': getattr(user.student, 'major', None)
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
        elif current_user.user_type == UserType.TEACHER.value and current_user.teacher:
            user_data['teacher_info'] = current_user.teacher.to_dict()
        
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
    """Enroll in a course"""
    try:
        data = request.get_json()
        
        if not data.get('class_id'):
            return jsonify({'message': 'class_id is required'}), 400
        
        if not current_user.student:
            return jsonify({'message': 'Student profile not found'}), 404
        
        class_obj = Class.query.get(data['class_id'])
        if not class_obj:
            return jsonify({'message': 'Class not found'}), 404
        
        if class_obj.status != ClassStatus.OPEN.value:
            return jsonify({'message': 'Class is not open for enrollment'}), 400
        
        if class_obj.current_enrollment >= class_obj.max_capacity:
            return jsonify({'message': 'Class is full'}), 400
        
        # Check if already enrolled
        existing_enrollment = Enrollment.query.filter_by(
            student_id=current_user.student.student_id,
            class_id=data['class_id']
        ).first()
        
        if existing_enrollment:
            if existing_enrollment.status == EnrollmentStatus.REGISTERED.value:
                return jsonify({'message': 'Already enrolled in this class'}), 409
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
        
        return jsonify({
            'message': 'Successfully enrolled in class',
            'class_info': {
                'class_id': class_obj.class_id,
                'course_name': class_obj.course.course_name,
                'course_code': class_obj.course.course_code,
                'semester': class_obj.semester,
                'academic_year': class_obj.academic_year
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Enrollment failed', 'error': str(e)}), 500
@student_bp.route('/cancel-enrollment', methods=['POST'])
@student_required
def cancel_enrollment(current_user):
    """Cancel enrollment in a course"""
    try:
        data = request.get_json()
        
        if not data.get('class_id'):
            return error_response('MISSING_CLASS_ID', 'Yêu cầu cung cấp class_id.', 400)
        
        if not current_user.student:
            return error_response('STUDENT_NOT_FOUND', 'Hồ sơ sinh viên không tồn tại.', 404)
        
        # Verify class exists
        class_obj = Class.query.get(data['class_id'])
        if not class_obj:
            return error_response('CLASS_NOT_FOUND', 'Lớp học không tồn tại.', 404)
        
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
                {'class_id': data['class_id']},
                400
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
        
        # Optional: Check minimum credit requirement (example: 12 credits for full-time status)
        # Calculate current enrolled credits
        enrolled_classes = Enrollment.query.filter_by(
            student_id=current_user.student.student_id,
            status=EnrollmentStatus.REGISTERED.value
        ).all()
        total_credits = sum(
            Class.query.get(enrollment.class_id).course.credits
            for enrollment in enrolled_classes
            if enrollment.class_id != data['class_id']
        )
        # Assume minimum 12 credits required for full-time status
        if total_credits < 12:
            return error_response(
                'MINIMUM_CREDIT_VIOLATION',
                'Hủy đăng ký sẽ khiến tổng số tín chỉ dưới mức tối thiểu (12 tín chỉ).',
                {'current_credits': total_credits, 'minimum_required': 12}
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
    """Get available classes for enrollment"""
    try:
        # Get classes that are open and not full
        available_classes = Class.query.filter(
            Class.status == ClassStatus.OPEN.value,
            Class.current_enrollment < Class.max_capacity
        ).all()
        
        classes_data = []
        for class_obj in available_classes:
            # Check if student is already enrolled
            enrolled = Enrollment.query.filter_by(
                student_id=current_user.student.student_id if current_user.student else None,
                class_id=class_obj.class_id,
                status=EnrollmentStatus.REGISTERED.value
            ).first()
            
            if not enrolled:
                class_data = class_obj.to_dict()
                class_data['course_info'] = class_obj.course.to_dict()
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

@teacher_bp.route('/notifications', methods=['GET'])
@teacher_required
def get_teacher_notifications(current_user):
    """Get notifications for teachers"""
    try:
        # Mock notifications for teachers
        notifications = [
            {
                'id': 1,
                'title': 'Thông báo họp khoa',
                'content': 'Họp khoa định kỳ tháng 12 vào lúc 14:00 ngày 15/12/2024',
                'date': '2024-12-01',
                'type': 'meeting'
            },
            {
                'id': 2,
                'title': 'Thông báo chi trả lương',
                'content': 'Lương tháng 11 đã được chuyển vào tài khoản',
                'date': '2024-11-30',
                'type': 'salary'
            }
        ]
        
        return jsonify({
            'notifications': notifications
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to get notifications', 'error': str(e)}), 500

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
        
        return jsonify({
            'overview': {
                'total_students': total_students,
                'total_teachers': total_teachers,
                'total_courses': total_courses,
                'total_classes': total_classes,
                'active_classes': active_classes,
                'total_enrollments': total_enrollments
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': 'Failed to get overview', 'error': str(e)}), 500

# @manager_bp.route('/create-class', methods=['POST'])
# @manager_required
# def create_class(current_user):
#     """Create a new class"""
#     try:
#         data = request.get_json()
        
#         required_fields = ['course_id', 'semester', 'academic_year', 'max_capacity']
#         for field in required_fields:
#             if not data.get(field):
#                 return jsonify({'message': f'{field} is required'}), 400
        
#         # Verify course exists
#         course = Course.query.get(data['course_id'])
#         if not course:
#             return jsonify({'message': 'Course not found'}), 404
        
#         # Verify teacher exists (if provided)
#         teacher = None
#         if data.get('teacher_id'):
#             teacher = Teacher.query.get(data['teacher_id'])
#             if not teacher:
#                 return jsonify({'message': 'Teacher not found'}), 404
        
#         # Create new class
#         new_class = Class(
#             course_id=data['course_id'],
#             teacher_id=data.get('teacher_id'),
#             semester=data['semester'],
#             academic_year=data['academic_year'],
#             max_capacity=data['max_capacity'],
#             status=data.get('status', ClassStatus.OPEN.value)
#         )
        
#         db.session.add(new_class)
#         db.session.commit()
        
#         class_data = new_class.to_dict()
#         class_data['course_info'] = course.to_dict()
#         if teacher:
#             class_data['teacher_info'] = {
#                 'teacher_name': teacher.user.full_name,
#                 'department': teacher.department
#             }
        
#         return jsonify({
#             'message': 'Class created successfully',
#             'class': class_data
#         }), 201
        
#     except Exception as e:
#         db.session.rollback()
#         return jsonify({'message': 'Failed to create class', 'error': str(e)}), 500

@manager_bp.route('/assign-teacher', methods=['POST'])
@manager_required
def assign_teacher(current_user):
    """Assign teacher to a class"""
    try:
        data = request.get_json()
        
        if not data.get('class_id') or not data.get('teacher_id'):
            return jsonify({'message': 'class_id and teacher_id are required'}), 400
        
        # Verify class exists
        class_obj = Class.query.get(data['class_id'])
        if not class_obj:
            return jsonify({'message': 'Class not found'}), 404
        
        # Verify teacher exists
        teacher = Teacher.query.get(data['teacher_id'])
        if not teacher:
            return jsonify({'message': 'Teacher not found'}), 404
        
        # Assign teacher to class
        class_obj.teacher_id = data['teacher_id']
        db.session.commit()
        
        return jsonify({
            'message': 'Teacher assigned successfully',
            'class_id': class_obj.class_id,
            'teacher_name': teacher.user.full_name,
            'course_name': class_obj.course.course_name
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to assign teacher', 'error': str(e)}), 500

@manager_bp.route('/all-users', methods=['GET'])
@manager_required
def get_all_users(current_user):
    """Get all users in the system"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        user_type = request.args.get('user_type')
        
        query = User.query
        
        if user_type:
            query = query.filter_by(user_type=user_type)
        
        users = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        users_data = []
        for user in users.items:
            user_data = user.to_dict()
            
            # Add specific info based on user type
            if user.user_type == UserType.STUDENT.value and user.student:
                user_data['student_info'] = user.student.to_dict()
            elif user.user_type == UserType.TEACHER.value and user.teacher:
                user_data['teacher_info'] = user.teacher.to_dict()
            
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
        
        classes = Class.query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        classes_data = []
        for class_obj in classes.items:
            class_data = class_obj.to_dict()
            class_data['course_info'] = class_obj.course.to_dict()
            
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
from datetime import datetime
from flask import Blueprint, request, jsonify
from models import db, User, Student, Teacher, Course, Class, UserType, ClassStatus
from decorators import manager_required
from routes import error_response, success_response

# ====================== MANAGER ROUTES ======================

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
            return error_response('COURSE_NOT_FOUND', 'Khóa học không tồn tại.', 404)
        
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

@manager_bp.route('/update-class/<int:class_id>', methods=['PUT'])
@manager_required
def update_class(current_user, class_id):
    """Update class information with restrictions"""
    try:
        data = request.get_json()
        class_obj = Class.query.get(class_id)
        
        if not class_obj:
            return error_response('CLASS_NOT_FOUND', 'Lớp học không tồn tại.', 404)
        
        # Prevent updating course_id
        if 'course_id' in data:
            return error_response(
                'INVALID_UPDATE',
                'Không được phép cập nhật ID khóa học.',
                {'field': 'course_id'}
            )
        
        # Validate status update based on timing
        if 'status' in data:
            current_date = datetime.utcnow().date()
            try:
                start_date = class_obj.start_date
                end_date = class_obj.end_date
                
                if data['status'] == ClassStatus.COMPLETED.value and current_date < end_date:
                    return error_response(
                        'INVALID_STATUS_UPDATE',
                        'Không thể hoàn thành lớp học trước ngày kết thúc.',
                        {'current_date': current_date.isoformat(), 'end_date': end_date.isoformat()}
                    )
                if data['status'] == ClassStatus.OPEN.value and current_date > start_date:
                    return error_response(
                        'INVALID_STATUS_UPDATE',
                        'Không thể mở lại lớp học sau ngày bắt đầu.',
                        {'current_date': current_date.isoformat(), 'start_date': start_date.isoformat()}
                    )
            except AttributeError:
                return error_response(
                    'MISSING_DATES',
                    'Lớp học không có ngày bắt đầu hoặc kết thúc.',
                    {'class_id': class_id}
                )
        
        # Update allowed fields
        allowed_fields = ['semester', 'academic_year', 'max_capacity', 'start_date', 'end_date', 'status']
        for field in allowed_fields:
            if field in data:
                if field in ['start_date', 'end_date']:
                    try:
                        setattr(class_obj, field, datetime.strptime(data[field], '%Y-%m-%d').date())
                    except ValueError:
                        return error_response(
                            'INVALID_DATE_FORMAT',
                            f'Định dạng ngày không hợp lệ cho {field} (YYYY-MM-DD).'
                        )
                else:
                    setattr(class_obj, field, data[field])
        
        db.session.commit()
        
        class_data = class_obj.to_dict()
        class_data['course_info'] = class_obj.course.to_dict()
        
        return success_response(
            'Cập nhật lớp học thành công.',
            {'class': class_data}
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(
            'UPDATE_CLASS_FAILED',
            'Cập nhật lớp học thất bại.',
            {'error_details': str(e)},
            500
        )

@manager_bp.route('/add-student', methods=['POST'])
@manager_required
def add_student(current_user):
    """Add a new student"""
    try:
        data = request.get_json()
        
        required_fields = ['username', 'password', 'full_name', 'email', 'phone_number', 'major']
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
            major=data['major']
        )
        db.session.add(student)
        db.session.commit()
        
        user_data = user.to_dict()
        user_data['student_info'] = student.to_dict()
        
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

@manager_bp.route('/update-student/<int:student_id>', methods=['PUT'])
@manager_required
def update_student(current_user, student_id):
    """Update student information"""
    try:
        data = request.get_json()
        student = Student.query.get(student_id)
        
        if not student:
            return error_response('STUDENT_NOT_FOUND', 'Sinh viên không tồn tại.', 404)
        
        user = student.user
        
        # Validate updates
        if 'username' in data:
            return error_response(
                'INVALID_UPDATE',
                'Không được phép cập nhật tên đăng nhập.',
                {'field': 'username'}
            )
        
        if 'email' in data and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return error_response(
                    'EMAIL_EXISTS',
                    'Email đã được sử dụng.',
                    {'email': data['email']},
                    409
                )
        
        # Update allowed fields
        allowed_user_fields = ['full_name', 'email', 'phone_number']
        for field in allowed_user_fields:
            if field in data:
                setattr(user, field, data[field])
        
        if 'password' in data:
            user.set_password(data['password'])
        
        if 'major' in data:
            student.major = data['major']
        
        db.session.commit()
        
        user_data = user.to_dict()
        user_data['student_info'] = student.to_dict()
        
        return success_response(
            'Cập nhật thông tin sinh viên thành công.',
            {'user': user_data}
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(
            'UPDATE_STUDENT_FAILED',
            'Cập nhật thông tin sinh viên thất bại.',
            {'error_details': str(e)},
            500
        )

@manager_bp.route('/add-teacher', methods=['POST'])
@manager_required
def add_teacher(current_user):
    """Add a new teacher"""
    try:
        data = request.get_json()
        
        required_fields = ['username', 'password', 'full_name', 'email', 'phone_number', 'department']
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
            department=data['department']
        )
        db.session.add(teacher)
        db.session.commit()
        
        user_data = user.to_dict()
        user_data['teacher_info'] = teacher.to_dict()
        
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

@manager_bp.route('/update-teacher/<int:teacher_id>', methods=['PUT'])
@manager_required
def update_teacher(current_user, teacher_id):
    """Update teacher information"""
    try:
        data = request.get_json()
        teacher = Teacher.query.get(teacher_id)
        
        if not teacher:
            return error_response('TEACHER_NOT_FOUND', 'Giáo viên không tồn tại.', 404)
        
        user = teacher.user
        
        # Validate updates
        if 'username' in data:
            return error_response(
                'INVALID_UPDATE',
                'Không được phép cập nhật tên đăng nhập.',
                {'field': 'username'}
            )
        
        if 'email' in data and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return error_response(
                    'EMAIL_EXISTS',
                    'Email đã được sử dụng.',
                    {'email': data['email']},
                    409
                )
        
        # Update allowed fields
        allowed_user_fields = ['full_name', 'email', 'phone_number']
        for field in allowed_user_fields:
            if field in data:
                setattr(user, field, data[field])
        
        if 'password' in data:
            user.set_password(data['password'])
        
        if 'department' in data:
            teacher.department = data['department']
        
        db.session.commit()
        
        user_data = user.to_dict()
        user_data['teacher_info'] = teacher.to_dict()
        
        return success_response(
            'Cập nhật thông tin giáo viên thành công.',
            {'user': user_data}
        )
        
    except Exception as e:
        db.session.rollback()
        return error_response(
            'UPDATE_TEACHER_FAILED',
            'Cập nhật thông tin giáo viên thất bại.',
            {'error_details': str(e)},
            500
        )