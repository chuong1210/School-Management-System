# from flask import Blueprint, request, jsonify, current_app, make_response
# from flask_jwt_extended import (
#     create_access_token, create_refresh_token, jwt_required, 
#     get_jwt_identity, get_jwt
# )
# from datetime import datetime, timedelta
# from models import (
#     db, User, Student, Teacher, Course, Class, Schedule, Department,
#     Enrollment, UserType, ClassStatus, EnrollmentStatus
# )
# from decorators import (
#     token_required, student_required, teacher_required, 
#     manager_required, teacher_or_manager_required, blacklist_token
# )
# from helper_function import get_gpa_classification, calculate_system_health_score
# # Create Blueprint
# auth_bp = Blueprint('auth', __name__)
# student_bp = Blueprint('student', __name__)
# teacher_bp = Blueprint('teacher', __name__)
# manager_bp = Blueprint('manager', __name__)

# # Helper function for error responses
# def error_response(error_code, message, details=None, status_code=400):
#     """Standardized error response format"""
#     response_data = {
#         'error': error_code,
#         'message': message,
#         'timestamp': datetime.utcnow().isoformat(),
#         'status_code': status_code
#     }
#     if details:
#         response_data['details'] = details

#     response = make_response(jsonify(response_data), status_code)
#     response.headers["Content-Type"] = "application/json; charset=utf-8"
#     return response

# # Helper function for success responses
# def success_response(message, data=None, status_code=200):
#     """Standardized success response format"""
#     response_data = {
#         'success': True,
#         'message': message,
#         'timestamp': datetime.utcnow().isoformat(),
#         'status_code': status_code
#     }
#     if data:
#         response_data['data'] = data

#     response = make_response(jsonify(response_data), status_code)
#     response.headers["Content-Type"] = "application/json; charset=utf-8"
#     return response

# def validate_class_timing_constraints(class_obj, current_user_type, current_user):
#     """Validate class timing and enrollment constraints"""
#     current_date = datetime.utcnow().date()
    
#     # Check if class is within valid time frame for enrollment/teaching
#     if class_obj.start_date and class_obj.start_date < current_date:
#         if current_user_type == UserType.STUDENT.value:
#             # Students cannot enroll after class has started
#             return False, 'REGISTRATION_CLOSED', 'Không thể đăng ký vì lớp học đã bắt đầu.'
#         elif current_user_type == UserType.TEACHER.value:
#             # Allow teachers to view their ongoing classes
#             pass
    
#     # Check if class has ended
#     if class_obj.end_date and class_obj.end_date < current_date:
#         return False, 'CLASS_ENDED', 'Lớp học đã kết thúc.'
    
#     # Additional semester/academic year validation
#     current_semester = get_current_semester()  # You need to implement this
#     current_academic_year = get_current_academic_year()  # You need to implement this
    
#     if class_obj.semester != current_semester or class_obj.academic_year != current_academic_year:
#         if current_user_type == UserType.STUDENT.value:
#             return False, 'WRONG_SEMESTER', f'Lớp học thuộc học kì {class_obj.semester} năm học {class_obj.academic_year}.'
    
#     return True, None, None

# def get_current_semester():
#     """Get current semester based on current date"""
#     current_month = datetime.now().month
#     if 1 <= current_month <= 5:
#         return "Học kỳ 2"
#     elif 6 <= current_month <= 8:
#         return "Học kỳ hè"
#     else:
#         return "Học kỳ 1"

# def get_current_academic_year():
#     """Get current academic year"""
#     current_year = datetime.now().year
#     current_month = datetime.now().month
#     if current_month >= 9:
#         return f"{current_year}-{current_year + 1}"
#     else:
#         return f"{current_year - 1}-{current_year}"
# # ====================== AUTH ROUTES ======================

# @auth_bp.route('/register', methods=['POST'])
# def register():
#     """Register a new user"""
#     try:
#         data = request.get_json()
        
#         # Required fields validation
#         required_fields = ['username', 'password', 'full_name', 'user_type']
#         missing_fields = [field for field in required_fields if not data.get(field)]
#         if missing_fields:
#             return error_response(
#                 'MISSING_REQUIRED_FIELDS',
#                 'Thiếu các trường bắt buộc.',
#                 {'missing_fields': missing_fields, 'required_fields': required_fields}
#             )
        
#         # Check if username already exists
#         if User.query.filter_by(username=data['username']).first():
#             return error_response(
#                 'USERNAME_EXISTS',
#                 'Tên đăng nhập đã tồn tại.',
#                 {'username': data['username'], 'suggestion': 'Please choose a different username'},
#                 409
#             )
        
#         # Check if email already exists (if provided)
#         if data.get('email') and User.query.filter_by(email=data['email']).first():
#             return error_response(
#                 'EMAIL_EXISTS', 
#                 'Email đã được sử dụng.',
#                 {'email': data['email']},
#                 409
#             )
        
#         # Validate user type
#         valid_user_types = [e.value for e in UserType]
#         if data['user_type'] not in valid_user_types:
#             return error_response(
#                 'INVALID_USER_TYPE',
#                 'Loại người dùng không hợp lệ.',
#                 {'provided_type': data['user_type'], 'valid_types': valid_user_types}
#             )
        
#         # Create new user
#         user = User(
#             username=data['username'],
#             full_name=data['full_name'],
#             email=data.get('email'),
#             phone_number=data.get('phone_number'),
#             user_type=data['user_type']
#         )
#         user.set_password(data['password'])
        
#         db.session.add(user)
#         db.session.flush()  # Get user ID
        
#         # Create specific user type record
#         if data['user_type'] == UserType.STUDENT.value:
#             # Validate department for student
#             department_id = data.get('department_id')
#             if department_id:
#                 department = Department.query.get(department_id)
#                 if not department:
#                     return error_response(
#                         'DEPARTMENT_NOT_FOUND',
#                         'Khoa không tồn tại.',
#                         {'department_id': department_id}
#                     )
            
#             student = Student(
#                 user_id=user.user_id,
#                 student_code=data.get('student_code'),
#                 date_of_birth=datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date() if data.get('date_of_birth') else None,
#                 major=data.get('major'),
#                 enrollment_date=datetime.strptime(data['enrollment_date'], '%Y-%m-%d').date() if data.get('enrollment_date') else None,
#                 department_id=department_id
#             )
#             db.session.add(student)
            
#         elif data['user_type'] == UserType.TEACHER.value:
#             # Validate department for teacher
#             department_id = data.get('department_id')
#             if department_id:
#                 department = Department.query.get(department_id)
#                 if not department:
#                     return error_response(
#                         'DEPARTMENT_NOT_FOUND',
#                         'Khoa không tồn tại.',
#                         {'department_id': department_id}
#                     )
            
#             teacher = Teacher(
#                 user_id=user.user_id,
#                 teacher_code=data.get('teacher_code'),
#                 department=data.get('department'),  # Keep for backward compatibility
#                 hire_date=datetime.strptime(data['hire_date'], '%Y-%m-%d').date() if data.get('hire_date') else None,
#                 department_id=department_id
#             )
#             db.session.add(teacher)
        
#         db.session.commit()
        
#         return success_response(
#             'Đăng ký tài khoản thành công.',
#             {'user': user.to_dict()},
#             201
#         )
        
#     except Exception as e:
#         db.session.rollback()
#         return error_response(
#             'REGISTRATION_FAILED',
#             'Đăng ký thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# @auth_bp.route('/login', methods=['POST'])
# def login():
#     """User login"""
#     try:
#         data = request.get_json()
        
#         if not data.get('username') or not data.get('password'):
#             return error_response(
#                 'MISSING_CREDENTIALS',
#                 'Tên đăng nhập và mật khẩu là bắt buộc.',
#                 {'required_fields': ['username', 'password']}
#             )
        
#         user = User.query.filter_by(username=data['username']).first()
        
#         if not user or not user.check_password(data['password']):
#             return error_response(
#                 'INVALID_CREDENTIALS',
#                 'Tên đăng nhập hoặc mật khẩu không đúng.',
#                 {'username': data['username']},
#                 401
#             )
        
#         # Update last login
#         user.update_last_login()
        
#         # Get department info for claims
#         department_name = None
#         if user.teacher and user.teacher.department_id:
#             department = Department.query.get(user.teacher.department_id)
#             department_name = department.department_name if department else user.teacher.department
#         elif user.teacher:
#             department_name = user.teacher.department
        
#         claims = {
#             'username': user.username,
#             'user_type': user.user_type,
#             'full_name': user.full_name,
#             'department': department_name,
#         }
        
#         access_token = create_access_token(identity=str(user.user_id), additional_claims=claims)
#         refresh_token = create_refresh_token(identity=str(user.user_id))
        
#         # Get user-specific data
#         user_data = user.to_dict()
#         if user.user_type == UserType.STUDENT.value and user.student:
#             user_data['student_info'] = user.student.to_dict()
#             if user.student.department_id:
#                 department = Department.query.get(user.student.department_id)
#                 user_data['department_info'] = department.to_dict() if department else None
#         elif user.user_type == UserType.TEACHER.value and user.teacher:
#             user_data['teacher_info'] = user.teacher.to_dict()
#             if user.teacher.department_id:
#                 department = Department.query.get(user.teacher.department_id)
#                 user_data['department_info'] = department.to_dict() if department else None
        
#         return jsonify({
#             'message': 'Login successful',
#             'access_token': access_token,
#             'refresh_token': refresh_token,
#             'user': user_data
#         }), 200
        
#     except Exception as e:
#         return jsonify({'message': 'Login failed', 'error': str(e)}), 500

# @auth_bp.route('/refresh', methods=['POST'])
# @jwt_required(refresh=True)
# def refresh():
#     """Refresh access token"""
#     try:
#         current_user_id = get_jwt_identity()
#         user = User.query.get(current_user_id)
        
#         if not user:
#             return jsonify({'message': 'User not found'}), 404
        
#         # Get department info for claims
#         department_name = None
#         if user.teacher and user.teacher.department_id:
#             department = Department.query.get(user.teacher.department_id)
#             department_name = department.department_name if department else user.teacher.department
#         elif user.teacher:
#             department_name = user.teacher.department
        
#         new_access_token = create_access_token(
#             identity=current_user_id,
#             additional_claims={
#                 'username': user.username,
#                 'user_type': user.user_type,
#                 'full_name': user.full_name,
#                 'department': department_name,
#             }
#         )
        
#         return jsonify({
#             'access_token': new_access_token
#         }), 200
        
#     except Exception as e:
#         return jsonify({'message': 'Token refresh failed', 'error': str(e)}), 500

# @auth_bp.route('/logout', methods=['POST'])
# @jwt_required()
# def logout():
#     """User logout"""
#     try:
#         jti = get_jwt()['jti']
#         expires_delta = current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
        
#         if blacklist_token(jti, int(expires_delta.total_seconds())):
#             return jsonify({'message': 'Successfully logged out'}), 200
#         else:
#             return jsonify({'message': 'Logout failed'}), 500
            
#     except Exception as e:
#         return jsonify({'message': 'Logout failed', 'error': str(e)}), 500

# @auth_bp.route('/profile', methods=['GET'])
# @token_required
# def get_profile(current_user):
#     """Get current user profile"""
#     try:
#         user_data = current_user.to_dict()
        
#         # Add specific info based on user type
#         if current_user.user_type == UserType.STUDENT.value and current_user.student:
#             user_data['student_info'] = current_user.student.to_dict()
#             if current_user.student.department_id:
#                 department = Department.query.get(current_user.student.department_id)
#                 user_data['department_info'] = department.to_dict() if department else None
#         elif current_user.user_type == UserType.TEACHER.value and current_user.teacher:
#             user_data['teacher_info'] = current_user.teacher.to_dict()
#             if current_user.teacher.department_id:
#                 department = Department.query.get(current_user.teacher.department_id)
#                 user_data['department_info'] = department.to_dict() if department else None
        
#         return jsonify({
#             'user': user_data
#         }), 200
        
#     except Exception as e:
#         return jsonify({'message': 'Failed to get profile', 'error': str(e)}), 500

# # ====================== STUDENT ROUTES ======================


# @student_bp.route('/schedule', methods=['GET'])
# @student_required
# def get_student_schedule(current_user):
#     """Get student's class schedule"""
#     try:
#         if not current_user.student:
#             return jsonify({'message': 'Student profile not found'}), 404
        
#         # Get student's enrolled classes with schedules
#         enrollments = Enrollment.query.filter_by(
#             student_id=current_user.student.student_id,
#             status=EnrollmentStatus.REGISTERED.value
#         ).all()
        
#         schedule_data = []
#         for enrollment in enrollments:
#             class_obj = enrollment.class_ref
#             course = class_obj.course
#             schedules = class_obj.schedules
            
#             for schedule in schedules:
#                 schedule_data.append({
#                     'class_id': class_obj.class_id,
#                     'course_code': course.course_code,
#                     'course_name': course.course_name,
#                     'credits': course.credits,
#                     'day_of_week': schedule.day_of_week,
#                     'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
#                     'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
#                     'room_location': schedule.room_location,
#                     'semester': class_obj.semester,
#                     'academic_year': class_obj.academic_year
#                 })
        
#         return jsonify({
#             'schedule': schedule_data
#         }), 200
        
#     except Exception as e:
#         return jsonify({'message': 'Failed to get schedule', 'error': str(e)}), 500

# @student_bp.route('/enroll', methods=['POST'])
# @student_required
# def enroll_course(current_user):
#     """Enroll in a course with comprehensive validation"""
#     try:
#         data = request.get_json()
        
#         if not data.get('class_id'):
#             return error_response('MISSING_CLASS_ID', 'Yêu cầu cung cấp class_id.')
        
#         if not current_user.student:
#             return error_response('STUDENT_NOT_FOUND', 'Hồ sơ sinh viên không tồn tại.', status_code=404)
        
#         class_obj = Class.query.get(data['class_id'])
#         if not class_obj:
#             return error_response('CLASS_NOT_FOUND', 'Lớp học không tồn tại.', status_code=404)
        
#         # Check class status
#         if class_obj.status !=ClassStatus.OPEN.value:
#             return error_response('CLASS_NOT_OPEN', f'Lớp học không mở để đăng ký. Trạng thái hiện tại: {class_obj.status}')
        
#         # Check capacity
#         if class_obj.current_enrollment >= class_obj.max_capacity:
#             return error_response('CLASS_FULL', 'Lớp học đã đầy.')
        
#         # Validate timing constraints
#         is_valid, error_code, error_msg = validate_class_timing_constraints(
#             class_obj, UserType.STUDENT.value, current_user
#         )
#         if not is_valid:
#             return error_response(error_code, error_msg)
        
#         # CRITICAL: Check department match - student can only enroll in courses from their department
#         if not current_user.student.department_id:
#             return error_response(
#                 'STUDENT_NO_DEPARTMENT',
#                 'Sinh viên chưa được phân công khoa. Vui lòng liên hệ phòng đào tạo.'
#             )
        
#         if not class_obj.course.department_id:
#             return error_response(
#                 'COURSE_NO_DEPARTMENT',
#                 'Khóa học chưa được phân công khoa.'
#             )
        
#         if current_user.student.department_id != class_obj.course.department_id:
#             student_dept = Department.query.get(current_user.student.department_id)
#             course_dept = Department.query.get(class_obj.course.department_id)
#             return error_response(
#                 'DEPARTMENT_MISMATCH',
#                 'Bạn chỉ có thể đăng ký các lớp học thuộc khoa của mình.',
#                 {
#                     'student_department': student_dept.department_name if student_dept else 'Không xác định',
#                     'course_department': course_dept.department_name if course_dept else 'Không xác định',
#                     'student_department_id': current_user.student.department_id,
#                     'course_department_id': class_obj.course.department_id
#                 }
#             )
        
#         # Check if already enrolled
#         existing_enrollment = Enrollment.query.filter_by(
#             student_id=current_user.student.student_id,
#             class_id=data['class_id']
#         ).first()
        
#         if existing_enrollment:
#             if existing_enrollment.status == EnrollmentStatus.REGISTERED.value:
#                 return error_response('ALREADY_ENROLLED', 'Bạn đã đăng ký lớp học này.', status_code=409)
#             elif existing_enrollment.status in ['Đã hoàn thành', 'Rớt môn']:
#                 return error_response(
#                     'COURSE_COMPLETED',
#                     f'Bạn đã hoàn thành môn học này với trạng thái: {existing_enrollment.status}',
#                     status_code=409
#                 )
#             else:
#                 # Re-enroll if previously cancelled
#                 existing_enrollment.status = EnrollmentStatus.REGISTERED.value
#                 existing_enrollment.enrollment_date = datetime.utcnow()
#                 existing_enrollment.cancellation_date = None
#         else:
#             # Create new enrollment
#             enrollment = Enrollment(
#                 student_id=current_user.student.student_id,
#                 class_id=data['class_id'],
#                 status=EnrollmentStatus.REGISTERED.value,
#                 enrollment_date=datetime.utcnow()
#             )
#             db.session.add(enrollment)
        
#         # Update class enrollment count
#         class_obj.current_enrollment += 1
#         db.session.commit()
        
#         return success_response(
#             'Đăng ký lớp học thành công.',
#             {
#                 'class_info': {
#                     'class_id': class_obj.class_id,
#                     'course_name': class_obj.course.course_name,
#                     'course_code': class_obj.course.course_code,
#                     'semester': class_obj.semester,
#                     'academic_year': class_obj.academic_year,
#                     'start_date': class_obj.start_date.isoformat() if class_obj.start_date else None,
#                     'end_date': class_obj.end_date.isoformat() if class_obj.end_date else None
#                 }
#             }
#         )
        
#     except Exception as e:
#         db.session.rollback()
#         return error_response(
#             'ENROLL_FAILED',
#             'Đăng ký lớp học thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# @student_bp.route('/cancel-enrollment', methods=['POST'])
# @student_required
# def cancel_enrollment(current_user):
#     """Cancel enrollment with enhanced validation"""
#     try:
#         data = request.get_json()
        
#         if not data.get('class_id'):
#             return error_response('MISSING_CLASS_ID', 'Yêu cầu cung cấp class_id.')
        
#         if not current_user.student:
#             return error_response('STUDENT_NOT_FOUND', 'Hồ sơ sinh viên không tồn tại.', status_code=404)
        
#         class_obj = Class.query.get(data['class_id'])
#         if not class_obj:
#             return error_response('CLASS_NOT_FOUND', 'Lớp học không tồn tại.', status_code=404)
        
#         # Check if class allows cancellation (must be in registration period)
#         if class_obj.status not in [ClassStatus.OPEN.value,ClassStatus.IN_PROGRESS.value]:
#             return error_response(
#                 'CANCELLATION_NOT_ALLOWED',
#                 f'Không thể hủy đăng ký vì lớp học đã {class_obj.status.lower()}.',
#                 {'class_status': class_obj.status}
#             )
        
#         # Check if student is enrolled
#         enrollment = Enrollment.query.filter_by(
#             student_id=current_user.student.student_id,
#             class_id=data['class_id'],
#             status=EnrollmentStatus.REGISTERED.value
#         ).first()
        
#         if not enrollment:
#             return error_response(
#                 'NOT_ENROLLED',
#                 'Bạn chưa đăng ký lớp học này hoặc đăng ký đã bị hủy.',
#                 {'class_id': data['class_id']}
#             )
        
#         # ENHANCED: Check cancellation timing rules
#         current_date = datetime.utcnow().date()
        
#         # Rule 1: Cannot cancel after class has started
#         if class_obj.start_date and current_date >= class_obj.start_date:
#             days_since_start = (current_date - class_obj.start_date).days
#             if days_since_start > 14:  # Allow 14 days grace period
#                 return error_response(
#                     'CANCELLATION_PERIOD_EXPIRED',
#                     'Không thể hủy đăng ký vì đã quá thời hạn hủy (14 ngày sau ngày bắt đầu).',
#                     {
#                         'current_date': current_date.isoformat(),
#                         'start_date': class_obj.start_date.isoformat(),
#                         'days_since_start': days_since_start
#                     }
#                 )
        
#         # Rule 2: Cannot cancel if grade has been assigned
#         if enrollment.grade is not None or enrollment.score is not None:
#             return error_response(
#                 'GRADE_ASSIGNED',
#                 'Không thể hủy đăng ký vì điểm đã được ghi nhận.',
#                 {'class_id': data['class_id'], 'grade': enrollment.grade, 'score': enrollment.score}
#             )
        
#         # Rule 3: Check academic calendar constraints (implement as needed)
#         current_semester = get_current_semester()
#         current_academic_year = get_current_academic_year()
        
#         if class_obj.semester != current_semester or class_obj.academic_year != current_academic_year:
#             return error_response(
#                 'WRONG_ACADEMIC_PERIOD',
#                 'Không thể hủy đăng ký lớp học không thuộc kỳ học hiện tại.',
#                 {
#                     'class_semester': class_obj.semester,
#                     'class_academic_year': class_obj.academic_year,
#                     'current_semester': current_semester,
#                     'current_academic_year': current_academic_year
#                 }
#             )
        
#         # Update enrollment status
#         enrollment.status = EnrollmentStatus.CANCELLED.value
#         enrollment.cancellation_date = datetime.utcnow()
        
#         # Decrement class enrollment count
#         class_obj.current_enrollment = max(0, class_obj.current_enrollment - 1)
        
#         db.session.commit()
        
#         return success_response(
#             'Hủy đăng ký lớp học thành công.',
#             {
#                 'class_info': {
#                     'class_id': class_obj.class_id,
#                     'course_name': class_obj.course.course_name,
#                     'course_code': class_obj.course.course_code,
#                     'semester': class_obj.semester,
#                     'academic_year': class_obj.academic_year
#                 }
#             }
#         )
        
#     except Exception as e:
#         db.session.rollback()
#         return error_response(
#             'CANCEL_ENROLLMENT_FAILED',
#             'Hủy đăng ký lớp học thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# @student_bp.route('/available-classes', methods=['GET'])
# @student_required
# def get_available_classes(current_user):
#     """Get available classes with strict department filtering"""
#     try:
#         if not current_user.student:
#             return error_response('STUDENT_NOT_FOUND', 'Hồ sơ sinh viên không tồn tại.', status_code=404)
        
#         if not current_user.student.department_id:
#             return error_response(
#                 'STUDENT_NO_DEPARTMENT',
#                 'Sinh viên chưa được phân công khoa. Vui lòng liên hệ phòng đào tạo.'
#             )
        
#         # Get current academic period
#         current_semester = get_current_semester()
#         current_academic_year = get_current_academic_year()
#         current_date = datetime.utcnow().date()
        
#         # Query for available classes with strict filtering
#         query = Class.query.join(Course).filter(
#             # Basic availability criteria
#             Class.status == ClassStatus.OPEN.value,
#             Class.current_enrollment < Class.max_capacity,
#             # Department match - CRITICAL CONSTRAINT
#             Course.department_id == current_user.student.department_id,
#             # Current academic period only
#             Class.semester == current_semester,
#             Class.academic_year == current_academic_year,
#             # Registration should be before class starts
#             Class.start_date > current_date
#         )
        
#         available_classes = query.all()
        
#         classes_data = []
#         enrolled_class_ids = set()
        
#         # Get student's current enrollments
#         current_enrollments = Enrollment.query.filter_by(
#             student_id=current_user.student.student_id,
#             status=EnrollmentStatus.REGISTERED.value
#         ).all()
#         enrolled_class_ids = {e.class_id for e in current_enrollments}
        
#         for class_obj in available_classes:
#             # Skip already enrolled classes
#             if class_obj.class_id in enrolled_class_ids:
#                 continue
            
#             class_data = class_obj.to_dict()
#             class_data['course_info'] = class_obj.course.to_dict()
            
#             # Add department info
#             department = Department.query.get(class_obj.course.department_id)
#             class_data['department_info'] = department.to_dict() if department else None
            
#             # Add teacher info
#             if class_obj.teacher_id:
#                 teacher = Teacher.query.get(class_obj.teacher_id)
#                 if teacher:
#                     class_data['teacher_info'] = {
#                         'teacher_id': teacher.teacher_id,
#                         'teacher_name': teacher.user.full_name,
#                         'teacher_code': teacher.teacher_code,
#                         'department': teacher.department
#                     }
            
#             # Add schedule info
#             schedules = Schedule.query.filter_by(class_id=class_obj.class_id).all()
#             class_data['schedules'] = [
#                 {
#                     'day_of_week': s.day_of_week,
#                     'start_time': s.start_time.strftime('%H:%M') if s.start_time else None,
#                     'end_time': s.end_time.strftime('%H:%M') if s.end_time else None,
#                     'room_location': s.room_location
#                 } for s in schedules
#             ]
            
#             classes_data.append(class_data)
        
#         # Add summary information
#         student_department = Department.query.get(current_user.student.department_id)
        
#         return success_response(
#             'Lấy danh sách lớp học thành công.',
#             {
#                 'available_classes': classes_data,
#                 'summary': {
#                     'total_available': len(classes_data),
#                     'student_department': student_department.department_name if student_department else None,
#                     'current_semester': current_semester,
#                     'current_academic_year': current_academic_year
#                 }
#             }
#         )
        
#     except Exception as e:
#         return error_response(
#             'GET_AVAILABLE_CLASSES_FAILED',
#             'Lấy danh sách lớp học thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# # ====================== TEACHER ROUTES ======================


# @teacher_bp.route('/teaching-schedule', methods=['GET'])
# @teacher_required
# def get_teaching_schedule(current_user):
#     """Get teacher's teaching schedule with department validation"""
#     try:
#         if not current_user.teacher:
#             return error_response('TEACHER_NOT_FOUND', 'Hồ sơ giáo viên không tồn tại.', status_code=404)
        
#         semester = request.args.get('semester')
#         academic_year = request.args.get('academic_year')
        
#         # Base query for teacher's classes
#         query = Class.query.filter_by(teacher_id=current_user.teacher.teacher_id)
        
#         # Filter by semester and academic year if provided
#         if semester:
#             query = query.filter_by(semester=semester)
#         if academic_year:
#             query = query.filter_by(academic_year=academic_year)
        
#         classes = query.all()
        
#         schedule_data = []
#         for class_obj in classes:
#             course = class_obj.course
            
#             # Verify department match (should always match for existing data)
#             if (current_user.teacher.department_id and 
#                 course.department_id and 
#                 current_user.teacher.department_id != course.department_id):
#                 continue  # Skip mismatched departments
            
#             schedules = Schedule.query.filter_by(class_id=class_obj.class_id).all()
            
#             for schedule in schedules:
#                 schedule_data.append({
#                     'schedule_id': schedule.schedule_id,
#                     'class_id': class_obj.class_id,
#                     'course_code': course.course_code,
#                     'course_name': course.course_name,
#                     'credits': course.credits,
#                     'day_of_week': schedule.day_of_week,
#                     'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
#                     'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
#                     'room_location': schedule.room_location,
#                     'semester': class_obj.semester,
#                     'academic_year': class_obj.academic_year,
#                     'current_enrollment': class_obj.current_enrollment,
#                     'max_capacity': class_obj.max_capacity,
#                     'class_status': class_obj.status,
#                     'start_date': class_obj.start_date.isoformat() if class_obj.start_date else None,
#                     'end_date': class_obj.end_date.isoformat() if class_obj.end_date else None
#                 })
        
#         # Sort by day of week and start time
#         day_order = {'Thứ 2': 1, 'Thứ 3': 2, 'Thứ 4': 3, 'Thứ 5': 4, 'Thứ 6': 5, 'Thứ 7': 6, 'Chủ nhật': 7}
#         schedule_data.sort(key=lambda x: (day_order.get(x['day_of_week'], 8), x['start_time'] or '00:00'))
        
#         return success_response(
#             'Lấy lịch dạy thành công.',
#             {
#                 'teaching_schedule': schedule_data,
#                 'summary': {
#                     'total_classes': len(set(s['class_id'] for s in schedule_data)),
#                     'total_sessions': len(schedule_data)
#                 }
#             }
#         )
        
#     except Exception as e:
#         return error_response(
#             'GET_TEACHING_SCHEDULE_FAILED',
#             'Lấy lịch dạy thất bại.',
#             {'error_details': str(e)},
#             500
#         )


# @teacher_bp.route('/students', methods=['GET'])
# @teacher_required
# def get_teacher_students(current_user):
#     """Get students in teacher's classes"""
#     try:
#         if not current_user.teacher:
#             return jsonify({'message': 'Teacher profile not found'}), 404
        
#         # Get all students enrolled in teacher's classes
#         classes = Class.query.filter_by(teacher_id=current_user.teacher.teacher_id).all()
        
#         students_data = []
#         for class_obj in classes:
#             enrollments = Enrollment.query.filter_by(
#                 class_id=class_obj.class_id,
#                 status=EnrollmentStatus.REGISTERED.value
#             ).all()
            
#             for enrollment in enrollments:
#                 student = enrollment.student
#                 student_data = {
#                     'student_id': student.student_id,
#                     'student_code': student.student_code,
#                     'full_name': student.user.full_name,
#                     'email': student.user.email,
#                     'phone_number': student.user.phone_number,
#                     'major': student.major,
#                     'class_info': {
#                         'class_id': class_obj.class_id,
#                         'course_code': class_obj.course.course_code,
#                         'course_name': class_obj.course.course_name,
#                         'semester': class_obj.semester,
#                         'academic_year': class_obj.academic_year
#                     },
#                     'grade': enrollment.grade
#                 }
                
#                 # Add department info
#                 if student.department_id:
#                     department = Department.query.get(student.department_id)
#                     student_data['department_info'] = department.to_dict() if department else None
                
#                 students_data.append(student_data)
        
#         return jsonify({
#             'students': students_data
#         }), 200
        
#     except Exception as e:
#         return jsonify({'message': 'Failed to get students', 'error': str(e)}), 500

# @teacher_bp.route('/courses', methods=['GET'])
# @teacher_required
# def get_teacher_courses(current_user):
#     """Get courses assigned to teacher"""
#     try:
#         if not current_user.teacher:
#             return jsonify({'message': 'Teacher profile not found'}), 404
        
#         # Get teacher's classes and their courses
#         classes = Class.query.filter_by(teacher_id=current_user.teacher.teacher_id).all()
        
#         courses_data = []
#         course_ids = set()
        
#         for class_obj in classes:
#             if class_obj.course_id not in course_ids:
#                 course_ids.add(class_obj.course_id)
#                 course_data = class_obj.course.to_dict()
                
#                 # Add department info
#                 if class_obj.course.department_id:
#                     department = Department.query.get(class_obj.course.department_id)
#                     course_data['department_info'] = department.to_dict() if department else None
                
#                 # Add class information
#                 course_classes = [c for c in classes if c.course_id == class_obj.course_id]
#                 course_data['classes'] = [
#                     {
#                         'class_id': c.class_id,
#                         'semester': c.semester,
#                         'academic_year': c.academic_year,
#                         'current_enrollment': c.current_enrollment,
#                         'max_capacity': c.max_capacity,
#                         'status': c.status
#                     } for c in course_classes
#                 ]
                
#                 courses_data.append(course_data)
        
#         return jsonify({
#             'courses': courses_data
#         }), 200
        
#     except Exception as e:
#         return jsonify({'message': 'Failed to get courses', 'error': str(e)}), 500

# # ====================== MANAGER ROUTES ======================

# @manager_bp.route('/overview', methods=['GET'])
# @manager_required
# def get_system_overview(current_user):
#     """Get system overview statistics"""
#     try:
#         # Get statistics
#         total_students = Student.query.count()
#         total_teachers = Teacher.query.count()
#         total_courses = Course.query.count()
#         total_classes = Class.query.count()
#         active_classes = Class.query.filter_by(status=ClassStatus.OPEN.value).count()
#         total_enrollments = Enrollment.query.filter_by(status=EnrollmentStatus.REGISTERED.value).count()
#         total_departments = Department.query.count()
        
#         return jsonify({
#             'overview': {
#                 'total_students': total_students,
#                 'total_teachers': total_teachers,
#                 'total_courses': total_courses,
#                 'total_classes': total_classes,
#                 'active_classes': active_classes,
#                 'total_enrollments': total_enrollments,
#                 'total_departments': total_departments
#             }
#         }), 200
        
#     except Exception as e:
#         return jsonify({'message': 'Failed to get overview', 'error': str(e)}), 500

# @manager_bp.route('/departments', methods=['GET'])
# @manager_required
# def get_all_departments(current_user):
#     """Get all departments"""
#     try:
#         departments = Department.query.all()
#         departments_data = [dept.to_dict() for dept in departments]
        
#         return jsonify({
#             'departments': departments_data
#         }), 200
        
#     except Exception as e:
#         return jsonify({'message': 'Failed to get departments', 'error': str(e)}), 500

# @manager_bp.route('/create-class', methods=['POST'])
# @manager_required  
# def create_class(current_user):
#     """Create class with enhanced validation"""
#     try:
#         data = request.get_json()
        
#         required_fields = ['course_id', 'semester', 'academic_year', 'max_capacity', 'start_date', 'end_date']
#         missing_fields = [field for field in required_fields if not data.get(field)]
#         if missing_fields:
#             return error_response(
#                 'MISSING_REQUIRED_FIELDS',
#                 'Thiếu các trường bắt buộc.',
#                 {'missing_fields': missing_fields, 'required_fields': required_fields}
#             )
        
#         # Verify course exists
#         course = Course.query.get(data['course_id'])
#         if not course:
#             return error_response('COURSE_NOT_FOUND', 'Khóa học không tồn tại.', status_code=404)
        
#         # Validate dates
#         try:
#             start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
#             end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
#             if start_date >= end_date:
#                 return error_response(
#                     'INVALID_DATES',
#                     'Ngày bắt đầu phải trước ngày kết thúc.',
#                     {'start_date': data['start_date'], 'end_date': data['end_date']}
#                 )
            
#             # Validate semester timing
#             current_date = datetime.utcnow().date()
#             if start_date <= current_date:
#                 return error_response(
#                     'INVALID_START_DATE',
#                     'Ngày bắt đầu phải sau ngày hiện tại.',
#                     {'start_date': data['start_date'], 'current_date': current_date.isoformat()}
#                 )
                
#         except ValueError:
#             return error_response('INVALID_DATE_FORMAT', 'Định dạng ngày không hợp lệ (YYYY-MM-DD).')
        
#         # Validate capacity
#         if data['max_capacity'] <= 0:
#             return error_response('INVALID_CAPACITY', 'Sức chứa tối đa phải lớn hơn 0.')
        
#         # Validate semester format
#         valid_semesters = ['Học kỳ 1', 'Học kỳ 2', 'Học kỳ hè']
#         if data['semester'] not in valid_semesters:
#             return error_response(
#                 'INVALID_SEMESTER',
#                 'Học kỳ không hợp lệ.',
#                 {'provided_semester': data['semester'], 'valid_semesters': valid_semesters}
#             )
        
#         # Validate academic year format (YYYY-YYYY)
#         import re
#         academic_year_pattern = r'^\d{4}-\d{4}'
#         if not re.match(academic_year_pattern, data['academic_year']):
#             return error_response(
#                 'INVALID_ACADEMIC_YEAR',
#                 'Năm học không hợp lệ. Định dạng: YYYY-YYYY',
#                 {'provided_academic_year': data['academic_year']}
#             )
        
#         # Check for duplicate classes
#         existing_class = Class.query.filter_by(
#             course_id=data['course_id'],
#             semester=data['semester'],
#             academic_year=data['academic_year']
#         ).first()
        
#         if existing_class:
#             return error_response(
#                 'DUPLICATE_CLASS',
#                 'Đã tồn tại lớp học cho môn này trong học kỳ và năm học này.',
#                 {
#                     'existing_class_id': existing_class.class_id,
#                     'course_name': course.course_name
#                 },
#                 409
#             )

#         # Create new class
#         new_class = Class(
#             course_id=data['course_id'],
#             semester=data['semester'],
#             academic_year=data['academic_year'],
#             max_capacity=data['max_capacity'],
#             status=ClassStatus.OPEN.value,
#             start_date=start_date,
#             end_date=end_date,
#             current_enrollment=0
#         )
        
#         db.session.add(new_class)
#         db.session.flush()  # Get class ID
        
#         # Add schedules if provided
#         if data.get('schedules'):
#             for schedule_data in data['schedules']:
#                 try:
#                     schedule = Schedule(
#                         class_id=new_class.class_id,
#                         day_of_week=schedule_data['day_of_week'],
#                         start_time=datetime.strptime(schedule_data['start_time'], '%H:%M').time(),
#                         end_time=datetime.strptime(schedule_data['end_time'], '%H:%M').time(),
#                         room_location=schedule_data.get('room_location')
#                     )
#                     db.session.add(schedule)
#                 except (KeyError, ValueError) as e:
#                     db.session.rollback()
#                     return error_response(
#                         'INVALID_SCHEDULE_DATA',
#                         'Dữ liệu lịch học không hợp lệ.',
#                         {'error': str(e)}
#                     )
        
#         db.session.commit()
        
#         class_data = new_class.to_dict()
#         class_data['course_info'] = course.to_dict()
        
#         # Add department info
#         if course.department_id:
#             department = Department.query.get(course.department_id)
#             class_data['department_info'] = department.to_dict() if department else None
        
#         # Add schedules info
#         schedules = Schedule.query.filter_by(class_id=new_class.class_id).all()
#         class_data['schedules'] = [
#             {
#                 'schedule_id': s.schedule_id,
#                 'day_of_week': s.day_of_week,
#                 'start_time': s.start_time.strftime('%H:%M') if s.start_time else None,
#                 'end_time': s.end_time.strftime('%H:%M') if s.end_time else None,
#                 'room_location': s.room_location
#             } for s in schedules
#         ]
        
#         return success_response(
#             'Tạo lớp học thành công.',
#             {'class': class_data},
#             201
#         )
        
#     except Exception as e:
#         db.session.rollback()
#         return error_response(
#             'CREATE_CLASS_FAILED',
#             'Tạo lớp học thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# # ====================== ENHANCED MANAGER ROUTES ======================

# @manager_bp.route('/assign-teacher', methods=['POST'])
# @manager_required
# def assign_teacher(current_user):
#     """Assign teacher to class with strict department validation"""
#     try:
#         data = request.get_json()
        
#         required_fields = ['class_id', 'teacher_id']
#         missing_fields = [field for field in required_fields if not data.get(field)]
#         if missing_fields:
#             return error_response(
#                 'MISSING_REQUIRED_FIELDS',
#                 'class_id và teacher_id là bắt buộc.',
#                 {'missing_fields': missing_fields, 'required_fields': required_fields}
#             )
        
#         # Verify class exists
#         class_obj = Class.query.get(data['class_id'])
#         if not class_obj:
#             return error_response('CLASS_NOT_FOUND', 'Lớp học không tồn tại.', status_code=404)
        
#         # Verify teacher exists
#         teacher = Teacher.query.get(data['teacher_id'])
#         if not teacher:
#             return error_response('TEACHER_NOT_FOUND', 'Giáo viên không tồn tại.', status_code=404)
        
#         # CRITICAL: Check department match
#         if not teacher.department_id:
#             return error_response(
#                 'TEACHER_NO_DEPARTMENT',
#                 'Giáo viên chưa được phân công khoa. Vui lòng cập nhật thông tin giáo viên.'
#             )
        
#         if not class_obj.course.department_id:
#             return error_response(
#                 'COURSE_NO_DEPARTMENT',
#                 'Khóa học chưa được phân công khoa.'
#             )
        
#         if teacher.department_id != class_obj.course.department_id:
#             teacher_dept = Department.query.get(teacher.department_id)
#             course_dept = Department.query.get(class_obj.course.department_id)
#             return error_response(
#                 'DEPARTMENT_MISMATCH',
#                 'Giáo viên chỉ có thể dạy các lớp học thuộc khoa của mình.',
#                 {
#                     'teacher_department': teacher_dept.department_name if teacher_dept else 'Không xác định',
#                     'course_department': course_dept.department_name if course_dept else 'Không xác định',
#                     'teacher_department_id': teacher.department_id,
#                     'course_department_id': class_obj.course.department_id
#                 }
#             )
        
#         # Check if teacher is already assigned to another class at the same time
#         conflicting_classes = Class.query.join(Schedule).filter(
#             Class.teacher_id == teacher.teacher_id,
#             Class.semester == class_obj.semester,
#             Class.academic_year == class_obj.academic_year,
#             Class.class_id != class_obj.class_id
#         ).all()
        
#         # Get schedules for the class being assigned
#         new_schedules = Schedule.query.filter_by(class_id=class_obj.class_id).all()
        
#         for conflict_class in conflicting_classes:
#             conflict_schedules = Schedule.query.filter_by(class_id=conflict_class.class_id).all()
            
#             # Check for time conflicts
#             for new_schedule in new_schedules:
#                 for conflict_schedule in conflict_schedules:
#                     if (new_schedule.day_of_week == conflict_schedule.day_of_week and
#                         new_schedule.start_time < conflict_schedule.end_time and
#                         new_schedule.end_time > conflict_schedule.start_time):
#                         return error_response(
#                             'SCHEDULE_CONFLICT',
#                             f'Giáo viên đã có lịch dạy trùng vào {new_schedule.day_of_week} từ {conflict_schedule.start_time} đến {conflict_schedule.end_time}.',
#                             {
#                                 'conflicting_class_id': conflict_class.class_id,
#                                 'conflicting_course': conflict_class.course.course_name
#                             }
#                         )
        
#         # Assign teacher to class
#         class_obj.teacher_id = data['teacher_id']
#         db.session.commit()
        
#         return success_response(
#             'Phân công giáo viên thành công.',
#             {
#                 'class_id': class_obj.class_id,
#                 'course_name': class_obj.course.course_name,
#                 'teacher_info': {
#                     'teacher_id': teacher.teacher_id,
#                     'teacher_name': teacher.user.full_name,
#                     'teacher_code': teacher.teacher_code,
#                     'department': teacher_dept.department_name if teacher_dept else None
#                 }
#             }
#         )
        
#     except Exception as e:
#         db.session.rollback()
#         return error_response(
#             'ASSIGN_TEACHER_FAILED',
#             'Phân công giáo viên thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# @manager_bp.route('/add-student', methods=['POST'])
# @manager_required
# def add_student(current_user):
#     """Add a new student"""
#     try:
#         data = request.get_json()
        
#         required_fields = ['username', 'password', 'full_name', 'email', 'phone_number', 'major', 'department_id']
#         missing_fields = [field for field in required_fields if not data.get(field)]
#         if missing_fields:
#             return error_response(
#                 'MISSING_REQUIRED_FIELDS',
#                 'Thiếu các trường bắt buộc.',
#                 {'missing_fields': missing_fields, 'required_fields': required_fields}
#             )
        
#         # Check if username exists
#         if User.query.filter_by(username=data['username']).first():
#             return error_response(
#                 'USERNAME_EXISTS',
#                 'Tên đăng nhập đã tồn tại.',
#                 {'username': data['username']},
#                 409
#             )
        
#         # Check if email exists
#         if User.query.filter_by(email=data['email']).first():
#             return error_response(
#                 'EMAIL_EXISTS',
#                 'Email đã được sử dụng.',
#                 {'email': data['email']},
#                 409
#             )
        
#         # Verify department exists
#         department = Department.query.get(data['department_id'])
#         if not department:
#             return error_response(
#                 'DEPARTMENT_NOT_FOUND',
#                 'Khoa không tồn tại.',
#                 {'department_id': data['department_id']},
#                 404
#             )
        
#         # Create user
#         user = User(
#             username=data['username'],
#             full_name=data['full_name'],
#             email=data['email'],
#             phone_number=data['phone_number'],
#             user_type=UserType.STUDENT.value
#         )
#         user.set_password(data['password'])
#         db.session.add(user)
#         db.session.flush()
        
#         # Create student
#         student = Student(
#             user_id=user.user_id,
#             major=data['major'],
#             department_id=data['department_id'],
#             student_code=data.get('student_code'),
#             date_of_birth=datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date() if data.get('date_of_birth') else None,
#             enrollment_date=datetime.strptime(data['enrollment_date'], '%Y-%m-%d').date() if data.get('enrollment_date') else None
#         )
#         db.session.add(student)
#         db.session.commit()
        
#         user_data = user.to_dict()
#         user_data['student_info'] = student.to_dict()
#         user_data['department_info'] = department.to_dict()
        
#         return success_response(
#             'Thêm sinh viên thành công.',
#             {'user': user_data},
#             201
#         )
        
#     except Exception as e:
#         db.session.rollback()
#         return error_response(
#             'ADD_STUDENT_FAILED',
#             'Thêm sinh viên thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# @manager_bp.route('/add-teacher', methods=['POST'])
# @manager_required
# def add_teacher(current_user):
#     """Add a new teacher"""
#     try:
#         data = request.get_json()
        
#         required_fields = ['username', 'password', 'full_name', 'email', 'phone_number', 'department', 'department_id']
#         missing_fields = [field for field in required_fields if not data.get(field)]
#         if missing_fields:
#             return error_response(
#                 'MISSING_REQUIRED_FIELDS',
#                 'Thiếu các trường bắt buộc.',
#                 {'missing_fields': missing_fields, 'required_fields': required_fields}
#             )
        
#         # Check if username exists
#         if User.query.filter_by(username=data['username']).first():
#             return error_response(
#                 'USERNAME_EXISTS',
#                 'Tên đăng nhập đã tồn tại.',
#                 {'username': data['username']},
#                 409
#             )
        
#         # Check if email exists
#         if User.query.filter_by(email=data['email']).first():
#             return error_response(
#                 'EMAIL_EXISTS',
#                 'Email đã được sử dụng.',
#                 {'email': data['email']},
#                 409
#             )
        
#         # Verify department exists
#         department = Department.query.get(data['department_id'])
#         if not department:
#             return error_response(
#                 'DEPARTMENT_NOT_FOUND',
#                 'Khoa không tồn tại.',
#                 {'department_id': data['department_id']},
#                 404
#             )
        
#         # Create user
#         user = User(
#             username=data['username'],
#             full_name=data['full_name'],
#             email=data['email'],
#             phone_number=data['phone_number'],
#             user_type=UserType.TEACHER.value
#         )
#         user.set_password(data['password'])
#         db.session.add(user)
#         db.session.flush()
        
#         # Create teacher
#         teacher = Teacher(
#             user_id=user.user_id,
#             department=data['department'],
#             department_id=data['department_id'],
#             teacher_code=data.get('teacher_code'),
#             hire_date=datetime.strptime(data['hire_date'], '%Y-%m-%d').date() if data.get('hire_date') else None
#         )
#         db.session.add(teacher)
#         db.session.commit()
        
#         user_data = user.to_dict()
#         user_data['teacher_info'] = teacher.to_dict()
#         user_data['department_info'] = department.to_dict()
        
#         return success_response(
#             'Thêm giáo viên thành công.',
#             {'user': user_data},
#             201
#         )
        
#     except Exception as e:
#         db.session.rollback()
#         return error_response(
#             'ADD_TEACHER_FAILED',
#             'Thêm giáo viên thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# @manager_bp.route('/all-users', methods=['GET'])
# @manager_required
# def get_all_users(current_user):
#     """Get all users in the system"""
#     try:
#         page = request.args.get('page', 1, type=int)
#         per_page = request.args.get('per_page', 20, type=int)
#         user_type = request.args.get('user_type')
#         department_id = request.args.get('department_id', type=int)
        
#         query = User.query
        
#         if user_type:
#             query = query.filter_by(user_type=user_type)
        
#         # Filter by department if specified
#         if department_id:
#             if user_type == UserType.STUDENT.value:
#                 query = query.join(Student).filter(Student.department_id == department_id)
#             elif user_type == UserType.TEACHER.value:
#                 query = query.join(Teacher).filter(Teacher.department_id == department_id)
        
#         users = query.paginate(
#             page=page, per_page=per_page, error_out=False
#         )
        
#         users_data = []
#         for user in users.items:
#             user_data = user.to_dict()
            
#             # Add specific info based on user type
#             if user.user_type == UserType.STUDENT.value and user.student:
#                 user_data['student_info'] = user.student.to_dict()
#                 if user.student.department_id:
#                     department = Department.query.get(user.student.department_id)
#                     user_data['department_info'] = department.to_dict() if department else None
#             elif user.user_type == UserType.TEACHER.value and user.teacher:
#                 user_data['teacher_info'] = user.teacher.to_dict()
#                 if user.teacher.department_id:
#                     department = Department.query.get(user.teacher.department_id)
#                     user_data['department_info'] = department.to_dict() if department else None
            
#             users_data.append(user_data)
        
#         return jsonify({
#             'users': users_data,
#             'pagination': {
#                 'page': users.page,
#                 'pages': users.pages,
#                 'per_page': users.per_page,
#                 'total': users.total,
#                 'has_next': users.has_next,
#                 'has_prev': users.has_prev
#             }
#         }), 200
        
#     except Exception as e:
#         return jsonify({'message': 'Failed to get users', 'error': str(e)}), 500

# @manager_bp.route('/all-classes', methods=['GET'])
# @manager_required
# def get_all_classes(current_user):
#     """Get all classes in the system"""
#     try:
#         page = request.args.get('page', 1, type=int)
#         per_page = request.args.get('per_page', 20, type=int)
#         department_id = request.args.get('department_id', type=int)
        
#         query = Class.query.join(Course)
        
#         # Filter by department if specified
#         if department_id:
#             query = query.filter(Course.department_id == department_id)
        
#         classes = query.paginate(
#             page=page, per_page=per_page, error_out=False
#         )
        
#         classes_data = []
#         for class_obj in classes.items:
#             class_data = class_obj.to_dict()
#             class_data['course_info'] = class_obj.course.to_dict()
            
#             # Add department info
#             if class_obj.course.department_id:
#                 department = Department.query.get(class_obj.course.department_id)
#                 class_data['department_info'] = department.to_dict() if department else None
            
#             if class_obj.teacher:
#                 class_data['teacher_info'] = {
#                     'teacher_name': class_obj.teacher.user.full_name,
#                     'department': class_obj.teacher.department
#                 }
            
#             classes_data.append(class_data)
        
#         return jsonify({
#             'classes': classes_data,
#             'pagination': {
#                 'page': classes.page,
#                 'pages': classes.pages,
#                 'per_page': classes.per_page,  
#                 'total': classes.total,
#                 'has_next': classes.has_next,
#                 'has_prev': classes.has_prev
#             }
#         }), 200
        
#     except Exception as e:
#         return jsonify({'message': 'Failed to get classes', 'error': str(e)}), 500

# @manager_bp.route('/create-course', methods=['POST'])
# @manager_required
# def create_course(current_user):
#     """Create a new course"""
#     try:
#         data = request.get_json()
        
#         required_fields = ['course_code', 'course_name', 'credits', 'department_id']
#         missing_fields = [field for field in required_fields if not data.get(field)]
#         if missing_fields:
#             return error_response(
#                 'MISSING_REQUIRED_FIELDS',
#                 'Thiếu các trường bắt buộc.',
#                 {'missing_fields': missing_fields, 'required_fields': required_fields}
#             )
        
#         # Check if course code exists
#         if Course.query.filter_by(course_code=data['course_code']).first():
#             return error_response(
#                 'COURSE_CODE_EXISTS',
#                 'Mã khóa học đã tồn tại.',
#                 {'course_code': data['course_code']},
#                 409
#             )
        
#         # Verify department exists
#         department = Department.query.get(data['department_id'])
#         if not department:
#             return error_response(
#                 'DEPARTMENT_NOT_FOUND',
#                 'Khoa không tồn tại.',
#                 {'department_id': data['department_id']},
#                 404
#             )
        
#         # Create course
#         course = Course(
#             course_code=data['course_code'],
#             course_name=data['course_name'],
#             credits=data['credits'],
#             description=data.get('description'),
#             department_id=data['department_id']
#         )
        
#         db.session.add(course)
#         db.session.commit()
        
#         course_data = course.to_dict()
#         course_data['department_info'] = department.to_dict()
        
#         return success_response(
#             'Tạo khóa học thành công.',
#             {'course': course_data},
#             201
#         )
        
#     except Exception as e:
#         db.session.rollback()
#         return error_response(
#             'CREATE_COURSE_FAILED',
#             'Tạo khóa học thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# @manager_bp.route('/grade-management', methods=['POST'])
# @manager_required
# def update_student_grade(current_user):
#     """Update student grades with validation"""
#     try:
#         data = request.get_json()
        
#         required_fields = ['enrollment_id', 'score']
#         missing_fields = [field for field in required_fields if not data.get(field)]
#         if missing_fields:
#             return error_response(
#                 'MISSING_REQUIRED_FIELDS',
#                 'enrollment_id và score là bắt buộc.',
#                 {'missing_fields': missing_fields, 'required_fields': required_fields}
#             )
        
#         # Find enrollment
#         enrollment = Enrollment.query.get(data['enrollment_id'])
#         if not enrollment:
#             return error_response('ENROLLMENT_NOT_FOUND', 'Đăng ký không tồn tại.', status_code=404)
        
#         # Validate score
#         score = float(data['score'])
#         if score < 0 or score > 10:
#             return error_response(
#                 'INVALID_SCORE',
#                 'Điểm số phải trong khoảng 0-10.',
#                 {'provided_score': score}
#             )
        
#         # Convert score to grade
#         if score >= 8.5:
#             grade = 'A'
#             status = EnrollmentStatus.COMPLETE.value
#         elif score >= 7.0:
#             grade = 'B'
#             status = EnrollmentStatus.COMPLETE.value
#         elif score >= 5.5:
#             grade = 'C'
#             status = EnrollmentStatus.COMPLETE.value
#         elif score >= 4.0:
#             grade = 'D'
#             status = EnrollmentStatus.COMPLETE.value
#         else:
#             grade = 'F'
#             status = EnrollmentStatus.Failed.value
        
#         # Update enrollment
#         enrollment.score = score
#         enrollment.grade = grade
#         enrollment.status = status
        
#         db.session.commit()
        
#         return success_response(
#             'Cập nhật điểm thành công.',
#             {
#                 'enrollment_id': enrollment.enrollment_id,
#                 'student_name': enrollment.student.user.full_name,
#                 'course_name': enrollment.class_ref.course.course_name,
#                 'score': score,
#                 'grade': grade,
#                 'status': status
#             }
#         )
        
#     except ValueError:
#         return error_response('INVALID_SCORE_FORMAT', 'Điểm số phải là số.')
#     except Exception as e:
#         db.session.rollback()
#         return error_response(
#             'UPDATE_GRADE_FAILED',
#             'Cập nhật điểm thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# @manager_bp.route('/department-statistics', methods=['GET'])
# @manager_required
# def get_department_statistics(current_user):
#     """Get comprehensive department statistics"""
#     try:
#         department_id = request.args.get('department_id', type=int)
#         semester = request.args.get('semester')
#         academic_year = request.args.get('academic_year')
        
#         # Base query for statistics
#         if department_id:
#             departments = [Department.query.get(department_id)]
#             if not departments[0]:
#                 return error_response('DEPARTMENT_NOT_FOUND', 'Khoa không tồn tại.', status_code=404)
#         else:
#             departments = Department.query.all()
        
#         statistics = []
#         for dept in departments:
#             if dept is None:
#                 continue
                
#             # Student count
#             student_count = Student.query.filter_by(department_id=dept.department_id).count()
            
#             # Teacher count  
#             teacher_count = Teacher.query.filter_by(department_id=dept.department_id).count()
            
#             # Course count
#             course_count = Course.query.filter_by(department_id=dept.department_id).count()
            
#             # Class count with optional filtering
#             class_query = Class.query.join(Course).filter(Course.department_id == dept.department_id)
#             if semester:
#                 class_query = class_query.filter(Class.semester == semester)
#             if academic_year:
#                 class_query = class_query.filter(Class.academic_year == academic_year)
            
#             class_count = class_query.count()
#             active_classes = class_query.filter(Class.status.in_([ClassStatus.OPEN, ClassStatus.IN_PROGRESS])).count()
            
#             # Enrollment statistics
#             enrollment_query = Enrollment.query.join(Class).join(Course).filter(
#                 Course.department_id == dept.department_id,
#                 Enrollment.status == EnrollmentStatus.REGISTERED.value
#             )
#             if semester:
#                 enrollment_query = enrollment_query.filter(Class.semester == semester)
#             if academic_year:
#                 enrollment_query = enrollment_query.filter(Class.academic_year == academic_year)
                
#             total_enrollments = enrollment_query.count()
            
#             # Grade distribution
#             grade_stats = {}
#             completed_enrollments = Enrollment.query.join(Class).join(Course).filter(
#                 Course.department_id == dept.department_id,
#                 Enrollment.status.in_([EnrollmentStatus.COMPLETE.value, EnrollmentStatus.Failed.value]),
#                 Enrollment.grade.isnot(None)
#             )
#             if semester:
#                 completed_enrollments = completed_enrollments.filter(Class.semester == semester)
#             if academic_year:
#                 completed_enrollments = completed_enrollments.filter(Class.academic_year == academic_year)
            
#             for enrollment in completed_enrollments:
#                 grade = enrollment.grade
#                 if grade in grade_stats:
#                     grade_stats[grade] += 1
#                 else:
#                     grade_stats[grade] = 1
            
#             dept_stats = {
#                 'department_info': dept.to_dict(),
#                 'student_count': student_count,
#                 'teacher_count': teacher_count,
#                 'course_count': course_count,
#                 'class_count': class_count,
#                 'active_classes': active_classes,
#                 'total_enrollments': total_enrollments,
#                 'grade_distribution': grade_stats,
#                 'completion_rate': round(
#                     (grade_stats.get('A', 0) + grade_stats.get('B', 0) + 
#                      grade_stats.get('C', 0) + grade_stats.get('D', 0)) / 
#                     max(sum(grade_stats.values()), 1) * 100, 2
#                 ) if grade_stats else 0
#             }
            
#             statistics.append(dept_stats)
        
#         return success_response(
#             'Lấy thống kê thành công.',
#             {
#                 'department_statistics': statistics,
#                 'filters_applied': {
#                     'department_id': department_id,
#                     'semester': semester,
#                     'academic_year': academic_year
#                 }
#             }
#         )
        
#     except Exception as e:
#         return error_response(
#             'GET_STATISTICS_FAILED',
#             'Lấy thống kê thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# # ====================== ENHANCED STUDENT ANALYTICS ROUTES ======================

# @student_bp.route('/gpa-by-semester', methods=['GET'])
# @student_required
# def get_student_gpa_by_semester(current_user):
#     """Get student's GPA by semester with class averages"""
#     try:
#         if not current_user.student:
#             return error_response('STUDENT_NOT_FOUND', 'Hồ sơ sinh viên không tồn tại.', status_code=404)
        
#         semester = request.args.get('semester')
#         academic_year = request.args.get('academic_year')
        
#         # Base query for student's completed enrollments
#         query = Enrollment.query.join(Class).join(Course).filter(
#             Enrollment.student_id == current_user.student.student_id,
#             Enrollment.status.in_(['Đã hoàn thành', 'Rớt môn']),
#             Enrollment.score.isnot(None)
#         )
        
#         # Filter by semester/academic year if provided
#         if semester:
#             query = query.filter(Class.semester == semester)
#         if academic_year:
#             query = query.filter(Class.academic_year == academic_year)
        
#         enrollments = query.all()
        
#         if not enrollments:
#             return success_response(
#                 'Chưa có dữ liệu điểm.',
#                 {
#                     'student_gpa': None,
#                     'courses': [],
#                     'summary': {
#                         'total_courses': 0,
#                         'total_credits': 0,
#                         'semester': semester,
#                         'academic_year': academic_year
#                     }
#                 }
#             )
        
#         # Calculate student GPA
#         total_points = 0
#         total_credits = 0
#         course_details = []
        
#         for enrollment in enrollments:
#             course = enrollment.class_ref.course
#             credits = course.credits
#             score = enrollment.score
            
#             # Calculate class average for comparison
#             class_enrollments = Enrollment.query.filter(
#                 Enrollment.class_id == enrollment.class_id,
#                 Enrollment.status.in_(['Đã hoàn thành', 'Rớt môn']),
#                 Enrollment.score.isnot(None)
#             ).all()
            
#             class_scores = [e.score for e in class_enrollments if e.score is not None]
#             class_average = sum(class_scores) / len(class_scores) if class_scores else 0
            
#             total_points += score * credits
#             total_credits += credits
            
#             course_details.append({
#                 'course_code': course.course_code,
#                 'course_name': course.course_name,
#                 'credits': credits,
#                 'student_score': score,
#                 'student_grade': enrollment.grade,
#                 'class_average': round(class_average, 2),
#                 'class_size': len(class_scores),
#                 'performance_vs_class': 'Trên trung bình' if score > class_average else 'Dưới trung bình' if score < class_average else 'Bằng trung bình',
#                 'semester': enrollment.class_ref.semester,
#                 'academic_year': enrollment.class_ref.academic_year
#             })
        
#         student_gpa = total_points / total_credits if total_credits > 0 else 0
        
#         return success_response(
#             'Lấy điểm trung bình thành công.',
#             {
#                 'student_gpa': round(student_gpa, 2),
#                 'courses': course_details,
#                 'summary': {
#                     'total_courses': len(enrollments),
#                     'total_credits': total_credits,
#                     'semester': semester,
#                     'academic_year': academic_year,
#                     'gpa_classification': get_gpa_classification(student_gpa)
#                 }
#             }
#         )
        
#     except Exception as e:
#         return error_response(
#             'GET_GPA_FAILED',
#             'Lấy điểm trung bình thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# @student_bp.route('/course-progress', methods=['GET'])
# @student_required
# def get_student_course_progress(current_user):
#     """Get student's course completion progress compared to department requirements"""
#     try:
#         if not current_user.student:
#             return error_response('STUDENT_NOT_FOUND', 'Hồ sơ sinh viên không tồn tại.', status_code=404)
        
#         if not current_user.student.department_id:
#             return error_response('STUDENT_NO_DEPARTMENT', 'Sinh viên chưa được phân công khoa.')
        
#         # Get all courses in student's department
#         all_department_courses = Course.query.filter_by(
#             department_id=current_user.student.department_id
#         ).all()
        
#         # Get student's completed courses
#         completed_enrollments = Enrollment.query.join(Class).join(Course).filter(
#             Enrollment.student_id == current_user.student.student_id,
#             Enrollment.status.in_(['Đã hoàn thành', 'Rớt môn']),
#             Course.department_id == current_user.student.department_id
#         ).all()
        
#         # Get currently enrolled courses
#         current_enrollments = Enrollment.query.join(Class).join(Course).filter(
#             Enrollment.student_id == current_user.student.student_id,
#             Enrollment.status == 'Đã đăng ký',
#             Course.department_id == current_user.student.department_id
#         ).all()
        
#         completed_course_ids = {e.class_ref.course_id for e in completed_enrollments}
#         current_course_ids = {e.class_ref.course_id for e in current_enrollments}
        
#         # Categorize courses
#         completed_courses = []
#         current_courses = []
#         remaining_courses = []
        
#         total_credits_required = 0
#         completed_credits = 0
#         current_credits = 0
#         passed_credits = 0
        
#         for course in all_department_courses:
#             total_credits_required += course.credits
            
#             if course.course_id in completed_course_ids:
#                 enrollment = next(e for e in completed_enrollments if e.class_ref.course_id == course.course_id)
#                 completed_courses.append({
#                     'course_code': course.course_code,
#                     'course_name': course.course_name,
#                     'credits': course.credits,
#                     'score': enrollment.score,
#                     'grade': enrollment.grade,
#                     'status': enrollment.status,
#                     'semester': enrollment.class_ref.semester,
#                     'academic_year': enrollment.class_ref.academic_year
#                 })
#                 completed_credits += course.credits
#                 if enrollment.status == 'Đã hoàn thành':
#                     passed_credits += course.credits
                    
#             elif course.course_id in current_course_ids:
#                 enrollment = next(e for e in current_enrollments if e.class_ref.course_id == course.course_id)
#                 current_courses.append({
#                     'course_code': course.course_code,
#                     'course_name': course.course_name,
#                     'credits': course.credits,
#                     'semester': enrollment.class_ref.semester,
#                     'academic_year': enrollment.class_ref.academic_year,
#                     'class_id': enrollment.class_id
#                 })
#                 current_credits += course.credits
                
#             else:
#                 remaining_courses.append({
#                     'course_code': course.course_code,
#                     'course_name': course.course_name,
#                     'credits': course.credits,
#                     'description': course.description
#                 })
        
#         # Calculate progress percentages
#         completion_percentage = (completed_credits / total_credits_required * 100) if total_credits_required > 0 else 0
#         pass_percentage = (passed_credits / total_credits_required * 100) if total_credits_required > 0 else 0
        
#         department = Department.query.get(current_user.student.department_id)
        
#         return success_response(
#             'Lấy tiến độ học tập thành công.',
#             {
#                 'progress_summary': {
#                     'department': department.department_name if department else None,
#                     'total_courses': len(all_department_courses),
#                     'completed_courses': len(completed_courses),
#                     'current_courses': len(current_courses),
#                     'remaining_courses': len(remaining_courses),
#                     'total_credits_required': total_credits_required,
#                     'completed_credits': completed_credits,
#                     'passed_credits': passed_credits,
#                     'current_credits': current_credits,
#                     'completion_percentage': round(completion_percentage, 1),
#                     'pass_percentage': round(pass_percentage, 1)
#                 },
#                 'completed_courses': completed_courses,
#                 'current_courses': current_courses,
#                 'remaining_courses': remaining_courses
#             }
#         )
        
#     except Exception as e:
#         return error_response(
#             'GET_COURSE_PROGRESS_FAILED',
#             'Lấy tiến độ học tập thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# # ====================== ENHANCED TEACHER ANALYTICS ROUTES ======================

# @teacher_bp.route('/class-enrollment-statistics', methods=['GET'])
# @teacher_required
# def get_class_enrollment_statistics(current_user):
#     """Get detailed class enrollment statistics for teacher"""
#     try:
#         if not current_user.teacher:
#             return error_response('TEACHER_NOT_FOUND', 'Hồ sơ giáo viên không tồn tại.', status_code=404)
        
#         semester = request.args.get('semester')
#         academic_year = request.args.get('academic_year')
        
#         # Get teacher's classes
#         query = Class.query.filter_by(teacher_id=current_user.teacher.teacher_id)
        
#         if semester:
#             query = query.filter_by(semester=semester)
#         if academic_year:
#             query = query.filter_by(academic_year=academic_year)
            
#         classes = query.all()
        
#         class_statistics = []
#         full_classes = 0
#         under_enrolled_classes = 0
#         total_students = 0
#         total_capacity = 0
        
#         for class_obj in classes:
#             # Get enrolled students
#             enrolled_students = Enrollment.query.filter_by(
#                 class_id=class_obj.class_id,
#                 status='Đã đăng ký'
#             ).all()
            
#             enrollment_percentage = (len(enrolled_students) / class_obj.max_capacity * 100) if class_obj.max_capacity > 0 else 0
            
#             # Categorize class by enrollment
#             if len(enrolled_students) >= class_obj.max_capacity:
#                 enrollment_status = 'Đầy'
#                 full_classes += 1
#             elif len(enrolled_students) >= class_obj.max_capacity * 0.8:
#                 enrollment_status = 'Gần đầy'
#             elif len(enrolled_students) >= class_obj.max_capacity * 0.5:
#                 enrollment_status = 'Vừa đủ'
#             else:
#                 enrollment_status = 'Thiếu sinh viên'
#                 under_enrolled_classes += 1
            
#             # Student list with department info
#             student_list = []
#             for enrollment in enrolled_students:
#                 student = enrollment.student
#                 department = Department.query.get(student.department_id) if student.department_id else None
#                 student_list.append({
#                     'student_id': student.student_id,
#                     'student_code': student.student_code,
#                     'full_name': student.user.full_name,
#                     'email': student.user.email,
#                     'major': student.major,
#                     'department': department.department_name if department else None,
#                     'enrollment_date': enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None
#                 })
            
#             total_students += len(enrolled_students)
#             total_capacity += class_obj.max_capacity
            
#             class_statistics.append({
#                 'class_info': {
#                     'class_id': class_obj.class_id,
#                     'course_code': class_obj.course.course_code,
#                     'course_name': class_obj.course.course_name,
#                     'semester': class_obj.semester,
#                     'academic_year': class_obj.academic_year,
#                     'status': class_obj.status
#                 },
#                 'enrollment_stats': {
#                     'current_enrollment': len(enrolled_students),
#                     'max_capacity': class_obj.max_capacity,
#                     'available_slots': class_obj.max_capacity - len(enrolled_students),
#                     'enrollment_percentage': round(enrollment_percentage, 1),
#                     'enrollment_status': enrollment_status
#                 },
#                 'students': student_list
#             })
        
#         # Overall statistics
#         overall_stats = {
#             'total_classes': len(classes),
#             'full_classes': full_classes,
#             'under_enrolled_classes': under_enrolled_classes,
#             'well_enrolled_classes': len(classes) - full_classes - under_enrolled_classes,
#             'total_students': total_students,
#             'total_capacity': total_capacity,
#             'overall_utilization': round((total_students / total_capacity * 100) if total_capacity > 0 else 0, 1)
#         }
        
#         return success_response(
#             'Lấy thống kê lớp học thành công.',
#             {
#                 'class_statistics': class_statistics,
#                 'overall_statistics': overall_stats,
#                 'filters_applied': {
#                     'semester': semester,
#                     'academic_year': academic_year
#                 }
#             }
#         )
        
#     except Exception as e:
#         return error_response(
#             'GET_CLASS_STATISTICS_FAILED',
#             'Lấy thống kê lớp học thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# @teacher_bp.route('/student-grades-analysis', methods=['GET'])
# @teacher_required
# def get_student_grades_analysis(current_user):
#     """Get detailed grade analysis for teacher's classes"""
#     try:
#         if not current_user.teacher:
#             return error_response('TEACHER_NOT_FOUND', 'Hồ sơ giáo viên không tồn tại.', status_code=404)
        
#         class_id = request.args.get('class_id', type=int)
#         semester = request.args.get('semester')
#         academic_year = request.args.get('academic_year')
        
#         # Get teacher's classes
#         query = Class.query.filter_by(teacher_id=current_user.teacher.teacher_id)
        
#         if class_id:
#             query = query.filter_by(class_id=class_id)
#         if semester:
#             query = query.filter_by(semester=semester)
#         if academic_year:
#             query = query.filter_by(academic_year=academic_year)
            
#         classes = query.all()
        
#         class_grade_analysis = []
        
#         for class_obj in classes:
#             # Get graded enrollments
#             graded_enrollments = Enrollment.query.filter(
#                 Enrollment.class_id == class_obj.class_id,
#                 Enrollment.status.in_(['Đã hoàn thành', 'Rớt môn']),
#                 Enrollment.score.isnot(None)
#             ).all()
            
#             if not graded_enrollments:
#                 class_grade_analysis.append({
#                     'class_info': {
#                         'class_id': class_obj.class_id,
#                         'course_code': class_obj.course.course_code,
#                         'course_name': class_obj.course.course_name,
#                         'semester': class_obj.semester,
#                         'academic_year': class_obj.academic_year
#                     },
#                     'grade_statistics': None,
#                     'student_grades': [],
#                     'message': 'Chưa có dữ liệu điểm'
#                 })
#                 continue
            
#             # Calculate statistics
#             scores = [e.score for e in graded_enrollments]
#             grade_counts = {}
#             for enrollment in graded_enrollments:
#                 grade = enrollment.grade
#                 grade_counts[grade] = grade_counts.get(grade, 0) + 1
            
#             # Grade distribution
#             grade_distribution = [
#                 {'grade': 'A', 'count': grade_counts.get('A', 0)},
#                 {'grade': 'B', 'count': grade_counts.get('B', 0)},
#                 {'grade': 'C', 'count': grade_counts.get('C', 0)},
#                 {'grade': 'D', 'count': grade_counts.get('D', 0)},
#                 {'grade': 'F', 'count': grade_counts.get('F', 0)}
#             ]
            
#             # Student details
#             student_grades = []
#             for enrollment in graded_enrollments:
#                 student = enrollment.student
#                 department = Department.query.get(student.department_id) if student.department_id else None
#                 student_grades.append({
#                     'student_id': student.student_id,
#                     'student_code': student.student_code,
#                     'full_name': student.user.full_name,
#                     'major': student.major,
#                     'department': department.department_name if department else None,
#                     'score': enrollment.score,
#                     'grade': enrollment.grade,
#                     'status': enrollment.status
#                 })
            
#             # Sort by score descending
#             student_grades.sort(key=lambda x: x['score'], reverse=True)
            
#             class_grade_analysis.append({
#                 'class_info': {
#                     'class_id': class_obj.class_id,
#                     'course_code': class_obj.course.course_code,
#                     'course_name': class_obj.course.course_name,
#                     'semester': class_obj.semester,
#                     'academic_year': class_obj.academic_year
#                 },
#                 'grade_statistics': {
#                     'total_students': len(graded_enrollments),
#                     'average_score': round(sum(scores) / len(scores), 2),
#                     'highest_score': max(scores),
#                     'lowest_score': min(scores),
#                     'pass_rate': round(sum(1 for s in scores if s >= 4.0) / len(scores) * 100, 1),
#                     'grade_distribution': grade_distribution
#                 },
#                 'student_grades': student_grades
#             })
        
#         return success_response(
#             'Lấy phân tích điểm số thành công.',
#             {
#                 'class_grade_analysis': class_grade_analysis,
#                 'filters_applied': {
#                     'class_id': class_id,
#                     'semester': semester,
#                     'academic_year': academic_year
#                 }
#             }
#         )
        
#     except Exception as e:
#         return error_response(
#             'GET_GRADE_ANALYSIS_FAILED',
#             'Lấy phân tích điểm số thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# # ====================== ENHANCED ADMIN ANALYTICS ROUTES ======================

# @manager_bp.route('/department-personnel-statistics', methods=['GET'])
# @manager_required
# def get_department_personnel_statistics(current_user):
#     """Get comprehensive personnel statistics by department"""
#     try:
#         department_id = request.args.get('department_id', type=int)
        
#         if department_id:
#             departments = [Department.query.get(department_id)]
#             if not departments[0]:
#                 return error_response('DEPARTMENT_NOT_FOUND', 'Khoa không tồn tại.', status_code=404)
#         else:
#             departments = Department.query.all()
        
#         personnel_statistics = []
#         total_students = 0
#         total_teachers = 0
        
#         for dept in departments:
#             if dept is None:
#                 continue
            
#             # Student statistics
#             students = Student.query.filter_by(department_id=dept.department_id).all()
#             student_count = len(students)
            
#             # Student by major distribution
#             major_distribution = {}
#             for student in students:
#                 major = student.major or 'Chưa xác định'
#                 major_distribution[major] = major_distribution.get(major, 0) + 1
            
#             # Teacher statistics
#             teachers = Teacher.query.filter_by(department_id=dept.department_id).all()
#             teacher_count = len(teachers)
            
#             # Course statistics
#             courses = Course.query.filter_by(department_id=dept.department_id).all()
#             total_credits = sum(course.credits for course in courses)
            
#             # Active classes this semester
#             current_semester = get_current_semester()
#             current_academic_year = get_current_academic_year()
            
#             active_classes = Class.query.join(Course).filter(
#                 Course.department_id == dept.department_id,
#                 Class.semester == current_semester,
#                 Class.academic_year == current_academic_year,
#                 Class.status.in_([ClassStatus.OPEN.value, ClassStatus.IN_PROGRESS.value])
#             ).count()
            
#             # Enrollment statistics
#             current_enrollments = Enrollment.query.join(Class).join(Course).filter(
#                 Course.department_id == dept.department_id,
#                 Class.semester == current_semester,
#                 Class.academic_year == current_academic_year,
#                 Enrollment.status == 'Đã đăng ký'
#             ).count()
            
#             total_students += student_count
#             total_teachers += teacher_count
            
#             personnel_statistics.append({
#                 'department_info': dept.to_dict(),
#                 'student_statistics': {
#                     'total_students': student_count,
#                     'major_distribution': [
#                         {'major': major, 'count': count}
#                         for major, count in major_distribution.items()
#                     ]
#                 },
#                 'teacher_statistics': {
#                     'total_teachers': teacher_count,
#                     'student_teacher_ratio': round(student_count / teacher_count, 1) if teacher_count > 0 else 0
#                 },
#                 'academic_statistics': {
#                     'total_courses': len(courses),
#                     'total_credits_offered': total_credits,
#                     'active_classes_current_semester': active_classes,
#                     'current_enrollments': current_enrollments
#                 }
#             })
        
#         return success_response(
#             'Lấy thống kê nhân sự thành công.',
#             {
#                 'department_personnel_statistics': personnel_statistics,
#                 'overall_summary': {
#                     'total_departments': len([d for d in departments if d is not None]),
#                     'total_students_all_departments': total_students,
#                     'total_teachers_all_departments': total_teachers,
#                     'overall_student_teacher_ratio': round(total_students / total_teachers, 1) if total_teachers > 0 else 0
#                 }
#             }
#         )
        
#     except Exception as e:
#         return error_response(
#             'GET_PERSONNEL_STATISTICS_FAILED',
#             'Lấy thống kê nhân sự thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# @manager_bp.route('/class-offering-statistics', methods=['GET'])
# @manager_required
# def get_class_offering_statistics(current_user):
#     """Get class offering statistics by department and semester"""
#     try:
#         department_id = request.args.get('department_id', type=int)
#         semester = request.args.get('semester')
#         academic_year = request.args.get('academic_year')
        
#         # Default to current semester if not specified
#         if not semester:
#             semester = get_current_semester()
#         if not academic_year:
#             academic_year = get_current_academic_year()
        
#         if department_id:
#             departments = [Department.query.get(department_id)]
#             if not departments[0]:
#                 return error_response('DEPARTMENT_NOT_FOUND', 'Khoa không tồn tại.', status_code=404)
#         else:
#             departments = Department.query.all()
        
#         class_statistics = []
#         total_classes_all_depts = 0
#         total_open_classes_all_depts = 0
#         total_enrollments_all_depts = 0
#         total_capacity_all_depts = 0
        
#         for dept in departments:
#             if dept is None:
#                 continue
            
#             # Get classes for this department and semester
#             classes_query = Class.query.join(Course).filter(
#                 Course.department_id == dept.department_id
#             )
            
#             if semester:
#                 classes_query = classes_query.filter(Class.semester == semester)
#             if academic_year:
#                 classes_query = classes_query.filter(Class.academic_year == academic_year)
            
#             classes = classes_query.all()
            
#             # Class status distribution
#             status_distribution = {
#                 ClassStatus.OPEN.value: 0,
#                ClassStatus.IN_PROGRESS.value: 0,
#                 ClassStatus.COMPLETED.value: 0
#             }
            
#             total_enrollment = 0
#             total_capacity = 0
#             full_classes = 0
#             under_enrolled_classes = 0
            
#             class_details = []
            
#             for class_obj in classes:
#                 status_distribution[class_obj.status] = status_distribution.get(class_obj.status, 0) + 1
                
#                 current_enrollment = class_obj.current_enrollment or 0
#                 max_capacity = class_obj.max_capacity or 0
                
#                 total_enrollment += current_enrollment
#                 total_capacity += max_capacity
                
#                 # Classification
#                 utilization = (current_enrollment / max_capacity * 100) if max_capacity > 0 else 0
#                 if utilization >= 100:
#                     full_classes += 1
#                     class_status = 'Đầy'
#                 elif utilization >= 80:
#                     class_status = 'Gần đầy'
#                 elif utilization >= 50:
#                     class_status = 'Vừa đủ'
#                 else:
#                     under_enrolled_classes += 1
#                     class_status = 'Thiếu sinh viên'
                
#                 # Teacher info
#                 teacher_info = None
#                 if class_obj.teacher_id:
#                     teacher = Teacher.query.get(class_obj.teacher_id)
#                     if teacher:
#                         teacher_info = {
#                             'teacher_name': teacher.user.full_name,
#                             'teacher_code': teacher.teacher_code
#                         }
                
#                 class_details.append({
#                     'class_id': class_obj.class_id,
#                     'course_code': class_obj.course.course_code,
#                     'course_name': class_obj.course.course_name,
#                     'credits': class_obj.course.credits,
#                     'current_enrollment': current_enrollment,
#                     'max_capacity': max_capacity,
#                     'utilization_percentage': round(utilization, 1),
#                     'class_status': class_status,
#                     'course_status': class_obj.status,
#                     'teacher_info': teacher_info,
#                     'start_date': class_obj.start_date.isoformat() if class_obj.start_date else None,
#                     'end_date': class_obj.end_date.isoformat() if class_obj.end_date else None
#                 })
            
#             open_classes = status_distribution.get('Mở đăng ký', 0) + status_distribution.get('Đang học', 0)
            
#             total_classes_all_depts += len(classes)
#             total_open_classes_all_depts += open_classes
#             total_enrollments_all_depts += total_enrollment
#             total_capacity_all_depts += total_capacity
            
#             class_statistics.append({
#                 'department_info': dept.to_dict(),
#                 'class_summary': {
#                     'total_classes': len(classes),
#                     'open_classes': open_classes,
#                     'completed_classes': status_distribution.get('Hoàn thành', 0),
#                     'status_distribution': [
#                         {'status': status, 'count': count}
#                         for status, count in status_distribution.items()
#                     ]
#                 },
#                 'enrollment_summary': {
#                     'total_enrollment': total_enrollment,
#                     'total_capacity': total_capacity,
#                     'utilization_rate': round((total_enrollment / total_capacity * 100) if total_capacity > 0 else 0, 1),
#                     'full_classes': full_classes,
#                     'under_enrolled_classes': under_enrolled_classes,
#                     'well_enrolled_classes': len(classes) - full_classes - under_enrolled_classes
#                 },
#                 'class_details': class_details
#             })
        
#         return success_response(
#             'Lấy thống kê lớp học thành công.',
#             {
#                 'class_offering_statistics': class_statistics,
#                 'overall_summary': {
#                     'total_departments': len([d for d in departments if d is not None]),
#                     'total_classes_all_departments': total_classes_all_depts,
#                     'total_open_classes_all_departments': total_open_classes_all_depts,
#                     'total_enrollments_all_departments': total_enrollments_all_depts,
#                     'total_capacity_all_departments': total_capacity_all_depts,
#                     'overall_utilization_rate': round((total_enrollments_all_depts / total_capacity_all_depts * 100) if total_capacity_all_depts > 0 else 0, 1)
#                 },
#                 'filters_applied': {
#                     'semester': semester,
#                     'academic_year': academic_year,
#                     'department_id': department_id
#                 }
#             }
#         )
        
#     except Exception as e:
#         return error_response(
#             'GET_CLASS_OFFERING_STATISTICS_FAILED',
#             'Lấy thống kê lớp học thất bại.',
#             {'error_details': str(e)},
#             500
#         )

# @manager_bp.route('/comprehensive-system-report', methods=['GET'])
# @manager_required
# def get_comprehensive_system_report(current_user):
#     """Generate comprehensive system report with all key metrics"""
#     try:
#         semester = request.args.get('semester')
#         academic_year = request.args.get('academic_year')
        
#         # Default to current semester if not specified
#         if not semester:
#             semester = get_current_semester()
#         if not academic_year:
#             academic_year = get_current_academic_year()
        
#         # 1. Overall System Statistics
#         total_departments = Department.query.count()
#         total_students = Student.query.count()
#         total_teachers = Teacher.query.count()
#         total_courses = Course.query.count()
#         total_users = User.query.count()
        
#         # 2. Current Semester Statistics
#         current_classes = Class.query.filter_by(
#             semester=semester,
#             academic_year=academic_year
#         ).count()
        
#         active_classes = Class.query.filter(
#             Class.semester == semester,
#             Class.academic_year == academic_year,
#             Class.status.in_([ClassStatus.OPEN.value, ClassStatus.IN_PROGRESS.value])
#         ).count()
        
#         current_enrollments = Enrollment.query.join(Class).filter(
#             Class.semester == semester,
#             Class.academic_year == academic_year,
#             Enrollment.status == EnrollmentStatus.REGISTERED.value
#         ).count()
        
#         # 3. Department-wise breakdown
#         departments = Department.query.all()
#         department_breakdown = []
        
#         for dept in departments:
#             dept_students = Student.query.filter_by(department_id=dept.department_id).count()
#             dept_teachers = Teacher.query.filter_by(department_id=dept.department_id).count()
#             dept_courses = Course.query.filter_by(department_id=dept.department_id).count()
            
#             dept_classes_current = Class.query.join(Course).filter(
#                 Course.department_id == dept.department_id,
#                 Class.semester == semester,
#                 Class.academic_year == academic_year
#             ).count()
            
#             dept_enrollments_current = Enrollment.query.join(Class).join(Course).filter(
#                 Course.department_id == dept.department_id,
#                 Class.semester == semester,
#                 Class.academic_year == academic_year,
#                 Enrollment.status == EnrollmentStatus.REGISTERED.value
#             ).count()
            
#             department_breakdown.append({
#                 'department_name': dept.department_name,
#                 'student_count': dept_students,
#                 'teacher_count': dept_teachers,
#                 'course_count': dept_courses,
#                 'current_classes': dept_classes_current,
#                 'current_enrollments': dept_enrollments_current,
#                 'student_teacher_ratio': round(dept_students / dept_teachers, 1) if dept_teachers > 0 else 0
#             })
        
#         # 4. Grade Statistics
#         grade_distribution = {}
#         completed_enrollments = Enrollment.query.join(Class).filter(
#             Class.semester == semester,
#             Class.academic_year == academic_year,
#             Enrollment.status.in_([EnrollmentStatus.COMPLETED.value, EnrollmentStatus.Failed.value]),
#             Enrollment.grade.isnot(None)
#         ).all()
        
#         for enrollment in completed_enrollments:
#             grade = enrollment.grade
#             grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
        
#         total_graded = sum(grade_distribution.values())
#         pass_count = sum(grade_distribution.get(grade, 0) for grade in ['A', 'B', 'C', 'D'])
        
#         # 5. System Health Indicators
#         # Classes without teachers
#         unassigned_classes = Class.query.filter(
#             Class.semester == semester,
#             Class.academic_year == academic_year,
#             Class.teacher_id.is_(None)
#         ).count()
        
#         # Students without department
#         students_without_dept = Student.query.filter(
#             Student.department_id.is_(None)
#         ).count()
        
#         # Teachers without department
#         teachers_without_dept = Teacher.query.filter(
#             Teacher.department_id.is_(None)
#         ).count()
        
#         # Under-enrolled classes (less than 50% capacity)
#         under_enrolled = Class.query.filter(
#             Class.semester == semester,
#             Class.academic_year == academic_year,
#             Class.current_enrollment < Class.max_capacity * 0.5,
#             Class.status.in_([ClassStatus.OPEN.value,ClassStatus.IN_PROGRESS.value])
#         ).count()
        
#         # 6. Trends (if historical data available)
#         previous_semester_enrollments = 0
#         try:
#             # Simple trend calculation - you may want to implement more sophisticated logic
#             if semester == 'Học kỳ 1':
#                 prev_semester = 'Học kỳ hè'
#                 prev_year = academic_year
#             elif semester == 'Học kỳ 2':
#                 prev_semester = 'Học kỳ 1'
#                 prev_year = academic_year
#             else:  # Học kỳ hè
#                 prev_semester = 'Học kỳ 2'
#                 year_parts = academic_year.split('-')
#                 prev_year = f"{int(year_parts[0])-1}-{int(year_parts[1])-1}"
            
#             previous_semester_enrollments = Enrollment.query.join(Class).filter(
#                 Class.semester == prev_semester,
#                 Class.academic_year == prev_year,
#                 Enrollment.status == EnrollmentStatus.REGISTERED.value
#             ).count()
#         except:
#             pass
        
#         enrollment_trend = 'Tăng' if current_enrollments > previous_semester_enrollments else 'Giảm' if current_enrollments < previous_semester_enrollments else 'Ổn định'
        
#         return success_response(
#             'Tạo báo cáo hệ thống thành công.',
#             {
#                 'report_metadata': {
#                     'generated_at': datetime.utcnow().isoformat(),
#                     'report_period': f"{semester} {academic_year}",
#                     'generated_by': current_user.full_name
#                 },
#                 'system_overview': {
#                     'total_departments': total_departments,
#                     'total_students': total_students,
#                     'total_teachers': total_teachers,
#                     'total_courses': total_courses,
#                     'total_users': total_users,
#                     'overall_student_teacher_ratio': round(total_students / total_teachers, 1) if total_teachers > 0 else 0
#                 },
#                 'current_semester_stats': {
#                     'semester': semester,
#                     'academic_year': academic_year,
#                     'total_classes': current_classes,
#                     'active_classes': active_classes,
#                     'total_enrollments': current_enrollments,
#                     'enrollment_trend': enrollment_trend,
#                     'enrollment_change': current_enrollments - previous_semester_enrollments
#                 },
#                 'department_breakdown': department_breakdown,
#                 'academic_performance': {
#                     'total_graded_enrollments': total_graded,
#                     'overall_pass_rate': round((pass_count / total_graded * 100) if total_graded > 0 else 0, 1),
#                     'grade_distribution': [
#                         {'grade': grade, 'count': count, 'percentage': round(count / total_graded * 100, 1)}
#                         for grade, count in grade_distribution.items()
#                     ] if total_graded > 0 else []
#                 },
#                 'system_health_indicators': {
#                     'unassigned_classes': unassigned_classes,
#                     'students_without_department': students_without_dept,
#                     'teachers_without_department': teachers_without_dept,
#                     'under_enrolled_classes': under_enrolled,
#                     'health_score': calculate_system_health_score(
#                         unassigned_classes, students_without_dept, 
#                         teachers_without_dept, under_enrolled, 
#                         current_classes, total_students, total_teachers
#                     )
#                 }
#             }
#         )
        
#     except Exception as e:
#         return error_response(
#             'GENERATE_SYSTEM_REPORT_FAILED',
#             'Tạo báo cáo hệ thống thất bại.',
#             {'error_details': str(e)},
#             500
#         )
# # ====================== ADDITIONAL VALIDATION ROUTES ======================

# @manager_bp.route('/validate-enrollment-conflicts', methods=['POST'])
# @manager_required
# def validate_enrollment_conflicts(current_user):
#     """Check for enrollment conflicts across the system"""
#     try:
#         # Find students enrolled in classes outside their department
#         department_conflicts = db.session.query(
#             Student.student_id,
#             User.full_name.label('student_name'),
#             Department.department_name.label('student_department'),
#             Course.course_name,
#             Department.department_name.label('course_department')
#         ).join(User, Student.user_id == User.user_id)\
#         .join(Department, Student.department_id == Department.department_id, isouter=True)\
#         .join(Enrollment, Student.student_id == Enrollment.student_id)\
#         .join(Class, Enrollment.class_id == Class.class_id)\
#         .join(Course, Class.course_id == Course.course_id)\
#         .join(Department.alias(), Course.department_id == Department.department_id, isouter=True)\
#         .filter(
#             Enrollment.status == EnrollmentStatus.REGISTERED.value,
#             Student.department_id != Course.department_id
#         ).all()
        
#         # Find teachers assigned to classes outside their department
#         teacher_conflicts = db.session.query(
#             Teacher.teacher_id,
#             User.full_name.label('teacher_name'),
#             Department.department_name.label('teacher_department'),
#             Course.course_name,
#             Department.department_name.label('course_department')
#         ).join(User, Teacher.user_id == User.user_id)\
#         .join(Department, Teacher.department_id == Department.department_id, isouter=True)\
#         .join(Class, Teacher.teacher_id == Class.teacher_id)\
#         .join(Course, Class.course_id == Course.course_id)\
#         .join(Department.alias(), Course.department_id == Department.department_id, isouter=True)\
#         .filter(
#             Teacher.department_id != Course.department_id
#         ).all()
        
#         conflicts_data = {
#             'student_department_conflicts': [
#                 {
#                     'student_id': conflict.student_id,
#                     'student_name': conflict.student_name,
#                     'student_department': conflict.student_department,
#                     'course_name': conflict.course_name,
#                     'course_department': conflict.course_department
#                 } for conflict in department_conflicts
#             ],
#             'teacher_department_conflicts': [
#                 {
#                     'teacher_id': conflict.teacher_id,
#                     'teacher_name': conflict.teacher_name,
#                     'teacher_department': conflict.teacher_department,
#                     'course_name': conflict.course_name,
#                     'course_department': conflict.course_department
#                 } for conflict in teacher_conflicts
#             ]
#         }
        
#         return success_response(
#             'Kiểm tra xung đột thành công.',
#             {
#                 'conflicts': conflicts_data,
#                 'summary': {
#                     'student_conflicts': len(department_conflicts),
#                     'teacher_conflicts': len(teacher_conflicts),
#                     'total_conflicts': len(department_conflicts) + len(teacher_conflicts)
#                 }
#             }
#         )
        
#     except Exception as e:
#         return error_response(
#             'VALIDATE_CONFLICTS_FAILED',
#             'Kiểm tra xung đột thất bại.',
#             {'error_details': str(e)},
#             500
#         )
# # ====================== EXPORT ROUTES ======================

# @manager_bp.route('/export-department-report', methods=['POST'])
# @manager_required
# def export_department_report(current_user):
#     """Export detailed department report"""
#     try:
#         data = request.get_json()
#         department_id = data.get('department_id')
#         semester = data.get('semester')
#         academic_year = data.get('academic_year')
#         export_format = data.get('format', 'json')  # json, csv options
        
#         if not department_id:
#             return error_response('MISSING_DEPARTMENT_ID', 'Cần cung cấp department_id.')
        
#         department = Department.query.get(department_id)
#         if not department:
#             return error_response('DEPARTMENT_NOT_FOUND', 'Khoa không tồn tại.', status_code=404)
        
#         # Collect comprehensive department data
#         students = Student.query.filter_by(department_id=department_id).all()
#         teachers = Teacher.query.filter_by(department_id=department_id).all()
#         courses = Course.query.filter_by(department_id=department_id).all()
        
#         # Classes data
#         classes_query = Class.query.join(Course).filter(Course.department_id == department_id)
#         if semester:
#             classes_query = classes_query.filter(Class.semester == semester)
#         if academic_year:
#             classes_query = classes_query.filter(Class.academic_year == academic_year)
#         classes = classes_query.all()
        
#         report_data = {
#             'department_info': department.to_dict(),
#             'export_metadata': {
#                 'generated_at': datetime.utcnow().isoformat(),
#                 'generated_by': current_user.full_name,
#                 'filters': {
#                     'semester': semester,
#                     'academic_year': academic_year
#                 }
#             },
#             'summary_statistics': {
#                 'total_students': len(students),
#                 'total_teachers': len(teachers),
#                 'total_courses': len(courses),
#                 'total_classes': len(classes)
#             },
#             'detailed_data': {
#                 'students': [
#                     {
#                         'student_code': s.student_code,
#                         'full_name': s.user.full_name,
#                         'email': s.user.email,
#                         'major': s.major,
#                         'enrollment_date': s.enrollment_date.isoformat() if s.enrollment_date else None
#                     } for s in students
#                 ],
#                 'teachers': [
#                     {
#                         'teacher_code': t.teacher_code,
#                         'full_name': t.user.full_name,
#                         'email': t.user.email,
#                         'department': t.department,
#                         'hire_date': t.hire_date.isoformat() if t.hire_date else None
#                     } for t in teachers
#                 ],
#                 'courses': [
#                     {
#                         'course_code': c.course_code,
#                         'course_name': c.course_name,
#                         'credits': c.credits,
#                         'description': c.description
#                     } for c in courses
#                 ],
#                 'classes': [
#                     {
#                         'class_id': c.class_id,
#                         'course_code': c.course.course_code,
#                         'course_name': c.course.course_name,
#                         'semester': c.semester,
#                         'academic_year': c.academic_year,
#                         'current_enrollment': c.current_enrollment,
#                         'max_capacity': c.max_capacity,
#                         'status': c.status,
#                         'teacher_name': c.teacher.user.full_name if c.teacher else None
#                     } for c in classes
#                 ]
#             }
#         }
        
#         return success_response(
#             'Xuất báo cáo khoa thành công.',
#             {
#                 'report_data': report_data,
#                 'export_format': export_format
#             }
#         )
        
#     except Exception as e:
#         return error_response(
#             'EXPORT_DEPARTMENT_REPORT_FAILED',
#             'Xuất báo cáo khoa thất bại.',
#             {'error_details': str(e)},
#             500
#         )