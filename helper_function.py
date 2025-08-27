
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