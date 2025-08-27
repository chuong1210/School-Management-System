from flask import Blueprint, request, jsonify
from models import (
    db, User, Student, Teacher, Course, Class, Schedule, Department,
    Enrollment, UserType, ClassStatus, EnrollmentStatus
)
from decorators import teacher_required

# Import helpers
from .helpers import error_response, success_response

teacher_bp = Blueprint('teacher', __name__)

# ====================== TEACHER ROUTES ======================


@teacher_bp.route('/teaching-schedule', methods=['GET'])
@teacher_required
def get_teaching_schedule(current_user):
    """Get teacher's teaching schedule with department validation"""
    try:
        if not current_user.teacher:
            return error_response('TEACHER_NOT_FOUND', 'Hồ sơ giáo viên không tồn tại.', status_code=404)
        
        semester = request.args.get('semester')
        academic_year = request.args.get('academic_year')
        
        # Base query for teacher's classes
        query = Class.query.filter_by(teacher_id=current_user.teacher.teacher_id)
        
        # Filter by semester and academic year if provided
        if semester:
            query = query.filter_by(semester=semester)
        if academic_year:
            query = query.filter_by(academic_year=academic_year)
        
        classes = query.all()
        
        schedule_data = []
        for class_obj in classes:
            course = class_obj.course
            
            # Verify department match (should always match for existing data)
            if (current_user.teacher.department_id and 
                course.department_id and 
                current_user.teacher.department_id != course.department_id):
                continue  # Skip mismatched departments
            
            schedules = Schedule.query.filter_by(class_id=class_obj.class_id).all()
            
            for schedule in schedules:
                schedule_data.append({
                    'schedule_id': schedule.schedule_id,
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
                    'max_capacity': class_obj.max_capacity,
                    'class_status': class_obj.status,
                    'start_date': class_obj.start_date.isoformat() if class_obj.start_date else None,
                    'end_date': class_obj.end_date.isoformat() if class_obj.end_date else None
                })
        
        # Sort by day of week and start time
        day_order = {'Thứ 2': 1, 'Thứ 3': 2, 'Thứ 4': 3, 'Thứ 5': 4, 'Thứ 6': 5, 'Thứ 7': 6, 'Chủ nhật': 7}
        schedule_data.sort(key=lambda x: (day_order.get(x['day_of_week'], 8), x['start_time'] or '00:00'))
        
        return success_response(
            'Lấy lịch dạy thành công.',
            {
                'teaching_schedule': schedule_data,
                'summary': {
                    'total_classes': len(set(s['class_id'] for s in schedule_data)),
                    'total_sessions': len(schedule_data)
                }
            }
        )
        
    except Exception as e:
        return error_response(
            'GET_TEACHING_SCHEDULE_FAILED',
            'Lấy lịch dạy thất bại.',
            {'error_details': str(e)},
            500
        )


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

@teacher_bp.route('/student-grades-analysis', methods=['GET'])
@teacher_required
def get_student_grades_analysis(current_user):
    """Get detailed grade analysis for teacher's classes"""
    try:
        if not current_user.teacher:
            return error_response('TEACHER_NOT_FOUND', 'Hồ sơ giáo viên không tồn tại.', status_code=404)
        
        class_id = request.args.get('class_id', type=int)
        semester = request.args.get('semester')
        academic_year = request.args.get('academic_year')
        
        # Get teacher's classes
        query = Class.query.filter_by(teacher_id=current_user.teacher.teacher_id)
        
        if class_id:
            query = query.filter_by(class_id=class_id)
        if semester:
            query = query.filter_by(semester=semester)
        if academic_year:
            query = query.filter_by(academic_year=academic_year)
            
        classes = query.all()
        
        class_grade_analysis = []
        
        for class_obj in classes:
            # Get graded enrollments
            graded_enrollments = Enrollment.query.filter(
                Enrollment.class_id == class_obj.class_id,
                Enrollment.status.in_(['Đã hoàn thành', 'Rớt môn']),
                Enrollment.score.isnot(None)
            ).all()
            
            if not graded_enrollments:
                class_grade_analysis.append({
                    'class_info': {
                        'class_id': class_obj.class_id,
                        'course_code': class_obj.course.course_code,
                        'course_name': class_obj.course.course_name,
                        'semester': class_obj.semester,
                        'academic_year': class_obj.academic_year
                    },
                    'grade_statistics': None,
                    'student_grades': [],
                    'message': 'Chưa có dữ liệu điểm'
                })
                continue
            
            # Calculate statistics
            scores = [e.score for e in graded_enrollments]
            grade_counts = {}
            for enrollment in graded_enrollments:
                grade = enrollment.grade
                grade_counts[grade] = grade_counts.get(grade, 0) + 1
            
            # Grade distribution
            grade_distribution = [
                {'grade': 'A', 'count': grade_counts.get('A', 0)},
                {'grade': 'B', 'count': grade_counts.get('B', 0)},
                {'grade': 'C', 'count': grade_counts.get('C', 0)},
                {'grade': 'D', 'count': grade_counts.get('D', 0)},
                {'grade': 'F', 'count': grade_counts.get('F', 0)}
            ]
            
            # Student details
            student_grades = []
            for enrollment in graded_enrollments:
                student = enrollment.student
                department = Department.query.get(student.department_id) if student.department_id else None
                student_grades.append({
                    'student_id': student.student_id,
                    'student_code': student.student_code,
                    'full_name': student.user.full_name,
                    'major': student.major,
                    'department': department.department_name if department else None,
                    'score': enrollment.score,
                    'grade': enrollment.grade,
                    'status': enrollment.status
                })
            
            # Sort by score descending
            student_grades.sort(key=lambda x: x['score'], reverse=True)
            
            class_grade_analysis.append({
                'class_info': {
                    'class_id': class_obj.class_id,
                    'course_code': class_obj.course.course_code,
                    'course_name': class_obj.course.course_name,
                    'semester': class_obj.semester,
                    'academic_year': class_obj.academic_year
                },
                'grade_statistics': {
                    'total_students': len(graded_enrollments),
                    'average_score': round(sum(scores) / len(scores), 2),
                    'highest_score': max(scores),
                    'lowest_score': min(scores),
                    'pass_rate': round(sum(1 for s in scores if s >= 4.0) / len(scores) * 100, 1),
                    'grade_distribution': grade_distribution
                },
                'student_grades': student_grades
            })
        
        return success_response(
            'Lấy phân tích điểm số thành công.',
            {
                'class_grade_analysis': class_grade_analysis,
                'filters_applied': {
                    'class_id': class_id,
                    'semester': semester,
                    'academic_year': academic_year
                }
            }
        )
        
    except Exception as e:
        return error_response(
            'GET_GRADE_ANALYSIS_FAILED',
            'Lấy phân tích điểm số thất bại.',
            {'error_details': str(e)},
            500
        )
@teacher_bp.route('/class-enrollment-statistics', methods=['GET'])
@teacher_required
def get_class_enrollment_statistics(current_user):
    """Get detailed class enrollment statistics for teacher"""
    try:
        if not current_user.teacher:
            return error_response('TEACHER_NOT_FOUND', 'Hồ sơ giáo viên không tồn tại.', status_code=404)
        
        semester = request.args.get('semester')
        academic_year = request.args.get('academic_year')
        
        # Get teacher's classes
        query = Class.query.filter_by(teacher_id=current_user.teacher.teacher_id)
        
        if semester:
            query = query.filter_by(semester=semester)
        if academic_year:
            query = query.filter_by(academic_year=academic_year)
            
        classes = query.all()
        
        class_statistics = []
        full_classes = 0
        under_enrolled_classes = 0
        total_students = 0
        total_capacity = 0
        
        for class_obj in classes:
            # Get enrolled students
            enrolled_students = Enrollment.query.filter_by(
                class_id=class_obj.class_id,
                status='Đã đăng ký'
            ).all()
            
            enrollment_percentage = (len(enrolled_students) / class_obj.max_capacity * 100) if class_obj.max_capacity > 0 else 0
            
            # Categorize class by enrollment
            if len(enrolled_students) >= class_obj.max_capacity:
                enrollment_status = 'Đầy'
                full_classes += 1
            elif len(enrolled_students) >= class_obj.max_capacity * 0.8:
                enrollment_status = 'Gần đầy'
            elif len(enrolled_students) >= class_obj.max_capacity * 0.5:
                enrollment_status = 'Vừa đủ'
            else:
                enrollment_status = 'Thiếu sinh viên'
                under_enrolled_classes += 1
            
            # Student list with department info
            student_list = []
            for enrollment in enrolled_students:
                student = enrollment.student
                department = Department.query.get(student.department_id) if student.department_id else None
                student_list.append({
                    'student_id': student.student_id,
                    'student_code': student.student_code,
                    'full_name': student.user.full_name,
                    'email': student.user.email,
                    'major': student.major,
                    'department': department.department_name if department else None,
                    'enrollment_date': enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None
                })
            
            total_students += len(enrolled_students)
            total_capacity += class_obj.max_capacity
            
            class_statistics.append({
                'class_info': {
                    'class_id': class_obj.class_id,
                    'course_code': class_obj.course.course_code,
                    'course_name': class_obj.course.course_name,
                    'semester': class_obj.semester,
                    'academic_year': class_obj.academic_year,
                    'status': class_obj.status
                },
                'enrollment_stats': {
                    'current_enrollment': len(enrolled_students),
                    'max_capacity': class_obj.max_capacity,
                    'available_slots': class_obj.max_capacity - len(enrolled_students),
                    'enrollment_percentage': round(enrollment_percentage, 1),
                    'enrollment_status': enrollment_status
                },
                'students': student_list
            })
        
        # Overall statistics
        overall_stats = {
            'total_classes': len(classes),
            'full_classes': full_classes,
            'under_enrolled_classes': under_enrolled_classes,
            'well_enrolled_classes': len(classes) - full_classes - under_enrolled_classes,
            'total_students': total_students,
            'total_capacity': total_capacity,
            'overall_utilization': round((total_students / total_capacity * 100) if total_capacity > 0 else 0, 1)
        }
        
        return success_response(
            'Lấy thống kê lớp học thành công.',
            {
                'class_statistics': class_statistics,
                'overall_statistics': overall_stats,
                'filters_applied': {
                    'semester': semester,
                    'academic_year': academic_year
                }
            }
        )
        
    except Exception as e:
        return error_response(
            'GET_CLASS_STATISTICS_FAILED',
            'Lấy thống kê lớp học thất bại.',
            {'error_details': str(e)},
            500
        )
