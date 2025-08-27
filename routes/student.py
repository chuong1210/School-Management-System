from flask import Blueprint, request, jsonify
from datetime import datetime
from models import (
    db, Enrollment, Class, Course, Department,
    UserType, ClassStatus, EnrollmentStatus
)
from decorators import student_required

# Import helpers từ file helpers.py
from .helpers import error_response, success_response, validate_class_timing_constraints, get_current_semester, get_current_academic_year, get_gpa_classification

student_bp = Blueprint('student', __name__)

# ====================== STUDENT ROUTES ======================


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
    """Enroll in a course with comprehensive validation"""
    try:
        data = request.get_json()
        
        if not data.get('class_id'):
            return error_response('MISSING_CLASS_ID', 'Yêu cầu cung cấp class_id.')
        
        if not current_user.student:
            return error_response('STUDENT_NOT_FOUND', 'Hồ sơ sinh viên không tồn tại.', status_code=404)
        
        class_obj = Class.query.get(data['class_id'])
        if not class_obj:
            return error_response('CLASS_NOT_FOUND', 'Lớp học không tồn tại.', status_code=404)
        
        # Check class status
        if class_obj.status !=ClassStatus.OPEN.value:
            return error_response('CLASS_NOT_OPEN', f'Lớp học không mở để đăng ký. Trạng thái hiện tại: {class_obj.status}')
        
        # Check capacity
        if class_obj.current_enrollment >= class_obj.max_capacity:
            return error_response('CLASS_FULL', 'Lớp học đã đầy.')
        
        # Validate timing constraints
        is_valid, error_code, error_msg = validate_class_timing_constraints(
            class_obj, UserType.STUDENT.value, current_user
        )
        if not is_valid:
            return error_response(error_code, error_msg)
        
        # CRITICAL: Check department match - student can only enroll in courses from their department
        if not current_user.student.department_id:
            return error_response(
                'STUDENT_NO_DEPARTMENT',
                'Sinh viên chưa được phân công khoa. Vui lòng liên hệ phòng đào tạo.'
            )
        
        if not class_obj.course.department_id:
            return error_response(
                'COURSE_NO_DEPARTMENT',
                'Khóa học chưa được phân công khoa.'
            )
        
        if current_user.student.department_id != class_obj.course.department_id:
            student_dept = Department.query.get(current_user.student.department_id)
            course_dept = Department.query.get(class_obj.course.department_id)
            return error_response(
                'DEPARTMENT_MISMATCH',
                'Bạn chỉ có thể đăng ký các lớp học thuộc khoa của mình.',
                {
                    'student_department': student_dept.department_name if student_dept else 'Không xác định',
                    'course_department': course_dept.department_name if course_dept else 'Không xác định',
                    'student_department_id': current_user.student.department_id,
                    'course_department_id': class_obj.course.department_id
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
            elif existing_enrollment.status in ['Đã hoàn thành', 'Rớt môn']:
                return error_response(
                    'COURSE_COMPLETED',
                    f'Bạn đã hoàn thành môn học này với trạng thái: {existing_enrollment.status}',
                    status_code=409
                )
            else:
                # Re-enroll if previously cancelled
                existing_enrollment.status = EnrollmentStatus.REGISTERED.value
                existing_enrollment.enrollment_date = datetime.utcnow()
                existing_enrollment.cancellation_date = None
        else:
            # Create new enrollment
            enrollment = Enrollment(
                student_id=current_user.student.student_id,
                class_id=data['class_id'],
                status=EnrollmentStatus.REGISTERED.value,
                enrollment_date=datetime.utcnow()
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
                    'academic_year': class_obj.academic_year,
                    'start_date': class_obj.start_date.isoformat() if class_obj.start_date else None,
                    'end_date': class_obj.end_date.isoformat() if class_obj.end_date else None
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
    """Cancel enrollment with enhanced validation"""
    try:
        data = request.get_json()
        
        if not data.get('class_id'):
            return error_response('MISSING_CLASS_ID', 'Yêu cầu cung cấp class_id.')
        
        if not current_user.student:
            return error_response('STUDENT_NOT_FOUND', 'Hồ sơ sinh viên không tồn tại.', status_code=404)
        
        class_obj = Class.query.get(data['class_id'])
        if not class_obj:
            return error_response('CLASS_NOT_FOUND', 'Lớp học không tồn tại.', status_code=404)
        
        # Check if class allows cancellation (must be in registration period)
        if class_obj.status not in [ClassStatus.OPEN.value,ClassStatus.IN_PROGRESS.value]:
            return error_response(
                'CANCELLATION_NOT_ALLOWED',
                f'Không thể hủy đăng ký vì lớp học đã {class_obj.status.lower()}.',
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
        
        # ENHANCED: Check cancellation timing rules
        current_date = datetime.utcnow().date()
        
        # Rule 1: Cannot cancel after class has started
        if class_obj.start_date and current_date >= class_obj.start_date:
            days_since_start = (current_date - class_obj.start_date).days
            if days_since_start > 14:  # Allow 14 days grace period
                return error_response(
                    'CANCELLATION_PERIOD_EXPIRED',
                    'Không thể hủy đăng ký vì đã quá thời hạn hủy (14 ngày sau ngày bắt đầu).',
                    {
                        'current_date': current_date.isoformat(),
                        'start_date': class_obj.start_date.isoformat(),
                        'days_since_start': days_since_start
                    }
                )
        
        # Rule 2: Cannot cancel if grade has been assigned
        if enrollment.grade is not None or enrollment.score is not None:
            return error_response(
                'GRADE_ASSIGNED',
                'Không thể hủy đăng ký vì điểm đã được ghi nhận.',
                {'class_id': data['class_id'], 'grade': enrollment.grade, 'score': enrollment.score}
            )
        
        # Rule 3: Check academic calendar constraints (implement as needed)
        current_semester = get_current_semester()
        current_academic_year = get_current_academic_year()
        
        if class_obj.semester != current_semester or class_obj.academic_year != current_academic_year:
            return error_response(
                'WRONG_ACADEMIC_PERIOD',
                'Không thể hủy đăng ký lớp học không thuộc kỳ học hiện tại.',
                {
                    'class_semester': class_obj.semester,
                    'class_academic_year': class_obj.academic_year,
                    'current_semester': current_semester,
                    'current_academic_year': current_academic_year
                }
            )
        
        # Update enrollment status
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
    """Get available classes with strict department filtering"""
    try:
        if not current_user.student:
            return error_response('STUDENT_NOT_FOUND', 'Hồ sơ sinh viên không tồn tại.', status_code=404)
        
        if not current_user.student.department_id:
            return error_response(
                'STUDENT_NO_DEPARTMENT',
                'Sinh viên chưa được phân công khoa. Vui lòng liên hệ phòng đào tạo.'
            )
        
        # Get current academic period
        current_semester = get_current_semester()
        current_academic_year = get_current_academic_year()
        current_date = datetime.utcnow().date()
        
        # Query for available classes with strict filtering
        query = Class.query.join(Course).filter(
            # Basic availability criteria
            Class.status == ClassStatus.OPEN.value,
            Class.current_enrollment < Class.max_capacity,
            # Department match - CRITICAL CONSTRAINT
            Course.department_id == current_user.student.department_id,
            # Current academic period only
            Class.semester == current_semester,
            Class.academic_year == current_academic_year,
            # Registration should be before class starts
            Class.start_date > current_date
        )
        
        available_classes = query.all()
        
        classes_data = []
        enrolled_class_ids = set()
        
        # Get student's current enrollments
        current_enrollments = Enrollment.query.filter_by(
            student_id=current_user.student.student_id,
            status=EnrollmentStatus.REGISTERED.value
        ).all()
        enrolled_class_ids = {e.class_id for e in current_enrollments}
        
        for class_obj in available_classes:
            # Skip already enrolled classes
            if class_obj.class_id in enrolled_class_ids:
                continue
            
            class_data = class_obj.to_dict()
            class_data['course_info'] = class_obj.course.to_dict()
            
            # Add department info
            department = Department.query.get(class_obj.course.department_id)
            class_data['department_info'] = department.to_dict() if department else None
            
            # Add teacher info
            if class_obj.teacher_id:
                teacher = Teacher.query.get(class_obj.teacher_id)
                if teacher:
                    class_data['teacher_info'] = {
                        'teacher_id': teacher.teacher_id,
                        'teacher_name': teacher.user.full_name,
                        'teacher_code': teacher.teacher_code,
                        'department': teacher.department
                    }
            
            # Add schedule info
            schedules = Schedule.query.filter_by(class_id=class_obj.class_id).all()
            class_data['schedules'] = [
                {
                    'day_of_week': s.day_of_week,
                    'start_time': s.start_time.strftime('%H:%M') if s.start_time else None,
                    'end_time': s.end_time.strftime('%H:%M') if s.end_time else None,
                    'room_location': s.room_location
                } for s in schedules
            ]
            
            classes_data.append(class_data)
        
        # Add summary information
        student_department = Department.query.get(current_user.student.department_id)
        
        return success_response(
            'Lấy danh sách lớp học thành công.',
            {
                'available_classes': classes_data,
                'summary': {
                    'total_available': len(classes_data),
                    'student_department': student_department.department_name if student_department else None,
                    'current_semester': current_semester,
                    'current_academic_year': current_academic_year
                }
            }
        )
        
    except Exception as e:
        return error_response(
            'GET_AVAILABLE_CLASSES_FAILED',
            'Lấy danh sách lớp học thất bại.',
            {'error_details': str(e)},
            500
        )

@student_bp.route('/gpa-by-semester', methods=['GET'])
@student_required
def get_student_gpa_by_semester(current_user):
    """Get student's GPA by semester with class averages"""
    try:
        if not current_user.student:
            return error_response('STUDENT_NOT_FOUND', 'Hồ sơ sinh viên không tồn tại.', status_code=404)
        
        semester = request.args.get('semester')
        academic_year = request.args.get('academic_year')
        
        # Base query for student's completed enrollments
        query = Enrollment.query.join(Class).join(Course).filter(
            Enrollment.student_id == current_user.student.student_id,
            Enrollment.status.in_(['Đã hoàn thành', 'Rớt môn']),
            Enrollment.score.isnot(None)
        )
        
        # Filter by semester/academic year if provided
        if semester:
            query = query.filter(Class.semester == semester)
        if academic_year:
            query = query.filter(Class.academic_year == academic_year)
        
        enrollments = query.all()
        
        if not enrollments:
            return success_response(
                'Chưa có dữ liệu điểm.',
                {
                    'student_gpa': None,
                    'courses': [],
                    'summary': {
                        'total_courses': 0,
                        'total_credits': 0,
                        'semester': semester,
                        'academic_year': academic_year
                    }
                }
            )
        
        # Calculate student GPA
        total_points = 0
        total_credits = 0
        course_details = []
        
        for enrollment in enrollments:
            course = enrollment.class_ref.course
            credits = course.credits
            score = enrollment.score
            
            # Calculate class average for comparison
            class_enrollments = Enrollment.query.filter(
                Enrollment.class_id == enrollment.class_id,
                Enrollment.status.in_(['Đã hoàn thành', 'Rớt môn']),
                Enrollment.score.isnot(None)
            ).all()
            
            class_scores = [e.score for e in class_enrollments if e.score is not None]
            class_average = sum(class_scores) / len(class_scores) if class_scores else 0
            
            total_points += score * credits
            total_credits += credits
            
            course_details.append({
                'course_code': course.course_code,
                'course_name': course.course_name,
                'credits': credits,
                'student_score': score,
                'student_grade': enrollment.grade,
                'class_average': round(class_average, 2),
                'class_size': len(class_scores),
                'performance_vs_class': 'Trên trung bình' if score > class_average else 'Dưới trung bình' if score < class_average else 'Bằng trung bình',
                'semester': enrollment.class_ref.semester,
                'academic_year': enrollment.class_ref.academic_year
            })
        
        student_gpa = total_points / total_credits if total_credits > 0 else 0
        
        return success_response(
            'Lấy điểm trung bình thành công.',
            {
                'student_gpa': round(student_gpa, 2),
                'courses': course_details,
                'summary': {
                    'total_courses': len(enrollments),
                    'total_credits': total_credits,
                    'semester': semester,
                    'academic_year': academic_year,
                    'gpa_classification': get_gpa_classification(student_gpa)
                }
            }
        )
        
    except Exception as e:
        return error_response(
            'GET_GPA_FAILED',
            'Lấy điểm trung bình thất bại.',
            {'error_details': str(e)},
            500
        )

@student_bp.route('/course-progress', methods=['GET'])
@student_required
def get_student_course_progress(current_user):
    """Get student's course completion progress compared to department requirements"""
    try:
        if not current_user.student:
            return error_response('STUDENT_NOT_FOUND', 'Hồ sơ sinh viên không tồn tại.', status_code=404)
        
        if not current_user.student.department_id:
            return error_response('STUDENT_NO_DEPARTMENT', 'Sinh viên chưa được phân công khoa.')
        
        # Get all courses in student's department
        all_department_courses = Course.query.filter_by(
            department_id=current_user.student.department_id
        ).all()
        
        # Get student's completed courses
        completed_enrollments = Enrollment.query.join(Class).join(Course).filter(
            Enrollment.student_id == current_user.student.student_id,
            Enrollment.status.in_(['Đã hoàn thành', 'Rớt môn']),
            Course.department_id == current_user.student.department_id
        ).all()
        
        # Get currently enrolled courses
        current_enrollments = Enrollment.query.join(Class).join(Course).filter(
            Enrollment.student_id == current_user.student.student_id,
            Enrollment.status == 'Đã đăng ký',
            Course.department_id == current_user.student.department_id
        ).all()
        
        completed_course_ids = {e.class_ref.course_id for e in completed_enrollments}
        current_course_ids = {e.class_ref.course_id for e in current_enrollments}
        
        # Categorize courses
        completed_courses = []
        current_courses = []
        remaining_courses = []
        
        total_credits_required = 0
        completed_credits = 0
        current_credits = 0
        passed_credits = 0
        
        for course in all_department_courses:
            total_credits_required += course.credits
            
            if course.course_id in completed_course_ids:
                enrollment = next(e for e in completed_enrollments if e.class_ref.course_id == course.course_id)
                completed_courses.append({
                    'course_code': course.course_code,
                    'course_name': course.course_name,
                    'credits': course.credits,
                    'score': enrollment.score,
                    'grade': enrollment.grade,
                    'status': enrollment.status,
                    'semester': enrollment.class_ref.semester,
                    'academic_year': enrollment.class_ref.academic_year
                })
                completed_credits += course.credits
                if enrollment.status == 'Đã hoàn thành':
                    passed_credits += course.credits
                    
            elif course.course_id in current_course_ids:
                enrollment = next(e for e in current_enrollments if e.class_ref.course_id == course.course_id)
                current_courses.append({
                    'course_code': course.course_code,
                    'course_name': course.course_name,
                    'credits': course.credits,
                    'semester': enrollment.class_ref.semester,
                    'academic_year': enrollment.class_ref.academic_year,
                    'class_id': enrollment.class_id
                })
                current_credits += course.credits
                
            else:
                remaining_courses.append({
                    'course_code': course.course_code,
                    'course_name': course.course_name,
                    'credits': course.credits,
                    'description': course.description
                })
        
        # Calculate progress percentages
        completion_percentage = (completed_credits / total_credits_required * 100) if total_credits_required > 0 else 0
        pass_percentage = (passed_credits / total_credits_required * 100) if total_credits_required > 0 else 0
        
        department = Department.query.get(current_user.student.department_id)
        
        return success_response(
            'Lấy tiến độ học tập thành công.',
            {
                'progress_summary': {
                    'department': department.department_name if department else None,
                    'total_courses': len(all_department_courses),
                    'completed_courses': len(completed_courses),
                    'current_courses': len(current_courses),
                    'remaining_courses': len(remaining_courses),
                    'total_credits_required': total_credits_required,
                    'completed_credits': completed_credits,
                    'passed_credits': passed_credits,
                    'current_credits': current_credits,
                    'completion_percentage': round(completion_percentage, 1),
                    'pass_percentage': round(pass_percentage, 1)
                },
                'completed_courses': completed_courses,
                'current_courses': current_courses,
                'remaining_courses': remaining_courses
            }
        )
        
    except Exception as e:
        return error_response(
            'GET_COURSE_PROGRESS_FAILED',
            'Lấy tiến độ học tập thất bại.',
            {'error_details': str(e)},
            500
        )