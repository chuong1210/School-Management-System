from datetime import datetime, timedelta
from flask import jsonify, make_response
from models import (
    db, User, Student, Teacher, Course, Class, Schedule, Department,
    Enrollment, UserType, ClassStatus, EnrollmentStatus
)
# ====================== RESPONSE HELPERS ======================
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

# ====================== VALIDATION & UTILITY HELPERS ======================
def get_gpa_classification(gpa):
    """Classify GPA into performance categories"""
    if gpa >= 8.5:
        return 'Xuất sắc'
    elif gpa >= 7.0:
        return 'Giỏi'
    elif gpa >= 5.5:
        return 'Khá'
    elif gpa >= 4.0:
        return 'Trung bình'
    else:
        return 'Yếu'

def calculate_system_health_score(unassigned_classes, students_without_dept, 
                                teachers_without_dept, under_enrolled, 
                                total_classes, total_students, total_teachers):
    """Calculate a system health score (0-100)"""
    score = 100
    
    # Deduct points for issues
    if total_classes > 0:
        score -= (unassigned_classes / total_classes) * 20  # 20% weight for unassigned classes
        score -= (under_enrolled / total_classes) * 15     # 15% weight for under-enrollment
    
    if total_students > 0:
        score -= (students_without_dept / total_students) * 10  # 10% weight
    
    if total_teachers > 0:
        score -= (teachers_without_dept / total_teachers) * 10  # 10% weight
    
    return max(0, round(score, 1))

def validate_class_timing_constraints(class_obj, current_user_type, current_user):
    """Validate class timing and enrollment constraints"""
    current_date = datetime.utcnow().date()
    
    # Check if class is within valid time frame for enrollment/teaching
    if class_obj.start_date and class_obj.start_date < current_date:
        if current_user_type == UserType.STUDENT.value:
            # Students cannot enroll after class has started
            return False, 'REGISTRATION_CLOSED', 'Không thể đăng ký vì lớp học đã bắt đầu.'
        elif current_user_type == UserType.TEACHER.value:
            # Allow teachers to view their ongoing classes
            pass
    
    # Check if class has ended
    if class_obj.end_date and class_obj.end_date < current_date:
        return False, 'CLASS_ENDED', 'Lớp học đã kết thúc.'
    
    # Additional semester/academic year validation
    current_semester = get_current_semester()  # You need to implement this
    current_academic_year = get_current_academic_year()  # You need to implement this
    
    if class_obj.semester != current_semester or class_obj.academic_year != current_academic_year:
        if current_user_type == UserType.STUDENT.value:
            return False, 'WRONG_SEMESTER', f'Lớp học thuộc học kì {class_obj.semester} năm học {class_obj.academic_year}.'
    
    return True, None, None

def get_current_semester():
    """Get current semester based on current date"""
    current_month = datetime.now().month
    if 1 <= current_month <= 5:
        return "Học kỳ 2"
    elif 6 <= current_month <= 8:
        return "Học kỳ hè"
    else:
        return "Học kỳ 1"

def get_current_academic_year():
    """Get current academic year"""
    current_year = datetime.now().year
    current_month = datetime.now().month
    if current_month >= 9:
        return f"{current_year}-{current_year + 1}"
    else:
        return f"{current_year - 1}-{current_year}"