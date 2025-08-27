from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt
from enum import Enum
from sqlalchemy import CheckConstraint

db = SQLAlchemy()

class UserType(Enum):
    STUDENT = "Học sinh"
    TEACHER = "Giáo viên"
    MANAGER = "Cán bộ quản lý"

class ClassStatus(Enum):
    OPEN = "Mở đăng ký"       # Enrollment Open
    IN_PROGRESS = "Đang học"  # In Progress
    COMPLETED = "Hoàn thành"  # Completed

class EnrollmentStatus(Enum):
    REGISTERED = "Đã đăng ký"
    CANCELLED = "Đã hủy"
    COMPLETE = "Đã hoàn thành"
    Failed ="Rớt môn"


class Department(db.Model):
    __tablename__ = 'department'
    
    department_id = db.Column('DepartmentID', db.Integer, primary_key=True, autoincrement=True)
    department_name = db.Column('DepartmentName', db.String(100), nullable=False, unique=True)
    
    # Relationships
    courses = db.relationship('Course', backref='department', cascade='all, delete-orphan')
    students = db.relationship('Student', backref='department')
    teachers = db.relationship('Teacher', backref='department')
    
    def to_dict(self):
        return {
            'department_id': self.department_id,
            'department_name': self.department_name
        }

class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column('UserID', db.Integer, primary_key=True, autoincrement=True)
    username = db.Column('Username', db.String(50), nullable=False, unique=True)
    password_hash = db.Column('PasswordHash', db.String(255), nullable=False)
    full_name = db.Column('FullName', db.String(100), nullable=False)
    email = db.Column('Email', db.String(100), unique=True)
    phone_number = db.Column('PhoneNumber', db.String(20))
    user_type = db.Column('UserType', db.String(20), nullable=False)
    date_created = db.Column('DateCreated', db.DateTime, default=datetime.utcnow)
    last_login = db.Column('LastLogin', db.DateTime)
    
    # Relationships
    student = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    teacher = db.relationship('Teacher', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def update_last_login(self):
        """Update last login time"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'full_name': self.full_name,
            'email': self.email,
            'phone_number': self.phone_number,
            'user_type': self.user_type,
            'date_created': self.date_created.isoformat() if self.date_created else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class Student(db.Model):
    __tablename__ = 'students'
    
    student_id = db.Column('StudentID', db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column('UserID', db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    student_code = db.Column('StudentCode', db.String(20), unique=True)
    date_of_birth = db.Column('DateOfBirth', db.Date)
    major = db.Column('Major', db.String(100))
    enrollment_date = db.Column('EnrollmentDate', db.Date)
    department_id = db.Column('DepartmentID', db.Integer, db.ForeignKey('department.DepartmentID'))
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='student', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'student_id': self.student_id,
            'user_id': self.user_id,
            'student_code': self.student_code,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'major': self.major,
            'enrollment_date': self.enrollment_date.isoformat() if self.enrollment_date else None,
            'department_id': self.department_id
        }

class Teacher(db.Model):
    __tablename__ = 'teachers'
    
    teacher_id = db.Column('TeacherID', db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column('UserID', db.Integer, db.ForeignKey('users.UserID'), nullable=False)
    teacher_code = db.Column('TeacherCode', db.String(20), unique=True)
    department = db.Column('Department', db.String(100))  # Kept for backward compatibility
    hire_date = db.Column('HireDate', db.Date)
    department_id = db.Column('DepartmentID', db.Integer, db.ForeignKey('department.DepartmentID'))
    
    # Relationships
    classes = db.relationship('Class', backref='teacher', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'teacher_id': self.teacher_id,
            'user_id': self.user_id,
            'teacher_code': self.teacher_code,
            'department': self.department,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'department_id': self.department_id
        }

class Course(db.Model):
    __tablename__ = 'courses'
    
    course_id = db.Column('CourseID', db.Integer, primary_key=True, autoincrement=True)
    course_code = db.Column('CourseCode', db.String(20), nullable=False, unique=True)
    course_name = db.Column('CourseName', db.String(200), nullable=False)
    credits = db.Column('Credits', db.Integer)
    description = db.Column('Description', db.Text)
    department_id = db.Column('DepartmentID', db.Integer, db.ForeignKey('department.DepartmentID'))
    
    # Relationships
    classes = db.relationship('Class', backref='course', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'course_id': self.course_id,
            'course_code': self.course_code,
            'course_name': self.course_name,
            'credits': self.credits,
            'description': self.description,
            'department_id': self.department_id
        }

class Class(db.Model):
    __tablename__ = 'classes'
    
    class_id = db.Column('ClassID', db.Integer, primary_key=True, autoincrement=True)
    course_id = db.Column('CourseID', db.Integer, db.ForeignKey('courses.CourseID'), nullable=False)
    teacher_id = db.Column('TeacherID', db.Integer, db.ForeignKey('teachers.TeacherID'))
    semester = db.Column('Semester', db.String(50), nullable=False)
    academic_year = db.Column('AcademicYear', db.String(10), nullable=False)
    max_capacity = db.Column('MaxCapacity', db.Integer)
    current_enrollment = db.Column('CurrentEnrollment', db.Integer, default=0)
    status = db.Column('Status', db.String(20), nullable=False)
    start_date = db.Column('StartDate', db.Date, nullable=False)
    end_date = db.Column('EndDate', db.Date, nullable=False)
    
    # Relationships
    schedules = db.relationship('Schedule', backref='class_ref', cascade='all, delete-orphan')
    enrollments = db.relationship('Enrollment', backref='class_ref', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'class_id': self.class_id,
            'course_id': self.course_id,
            'teacher_id': self.teacher_id,
            'semester': self.semester,
            'academic_year': self.academic_year,
            'max_capacity': self.max_capacity,
            'current_enrollment': self.current_enrollment,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None
        }

class Schedule(db.Model):
    __tablename__ = 'schedules'
    
    schedule_id = db.Column('ScheduleID', db.Integer, primary_key=True, autoincrement=True)
    class_id = db.Column('ClassID', db.Integer, db.ForeignKey('classes.ClassID'), nullable=False)
    day_of_week = db.Column('DayOfWeek', db.String(10), nullable=False)
    start_time = db.Column('StartTime', db.Time, nullable=False)
    end_time = db.Column('EndTime', db.Time, nullable=False)
    room_location = db.Column('RoomLocation', db.String(50))
    
    def to_dict(self):
        return {
            'schedule_id': self.schedule_id,
            'class_id': self.class_id,
            'day_of_week': self.day_of_week,
            'start_time': self.start_time.strftime('%H:%M:%S') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M:%S') if self.end_time else None,
            'room_location': self.room_location
        }

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    
    enrollment_id = db.Column('EnrollmentID', db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column('StudentID', db.Integer, db.ForeignKey('students.StudentID'), nullable=False)
    class_id = db.Column('ClassID', db.Integer, db.ForeignKey('classes.ClassID'), nullable=False)
    enrollment_date = db.Column('EnrollmentDate', db.DateTime, default=datetime.utcnow)
    grade = db.Column('Grade', db.String(5))
    status = db.Column('Status', db.String(20), nullable=False)
    cancellation_date = db.Column('CancellationDate', db.DateTime, default=datetime.utcnow)
    score = db.Column('Score', db.Float, nullable=True)

    __table_args__ = (
            db.UniqueConstraint('StudentID', 'ClassID', name='unique_student_class'),
            CheckConstraint('Score >= 0 AND Score <= 10', name='check_score_range')
        )    
    def to_dict(self):
        return {
            'enrollment_id': self.enrollment_id,
            'student_id': self.student_id,
            'class_id': self.class_id,
            'enrollment_date': self.enrollment_date.isoformat() if self.enrollment_date else None,
            'cancellation_date': self.cancellation_date.isoformat() if self.cancellation_date else None,
            'grade': self.grade,
            'status': self.status,
            'score': self.score

        }