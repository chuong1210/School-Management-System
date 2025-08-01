-- Initial database setup for School Management System

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS school_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE school_management;

-- Insert sample data

-- Sample Users
INSERT INTO users (Username, PasswordHash, FullName, Email, PhoneNumber, UserType, DateCreated) VALUES
('admin', '$2b$12$LQv3c1yqBwlVHpPjrCeyAueVuV/1zXtEIYqZe5rBhOwqMLwxo6QN2', 'Quản trị viên hệ thống', 'admin@school.edu.vn', '0123456789', 'Cán bộ quản lý', NOW()),
('student001', '$2b$12$LQv3c1yqBwlVHpPjrCeyAueVuV/1zXtEIYqZe5rBhOwqMLwxo6QN2', 'Nguyễn Văn An', 'student001@school.edu.vn', '0987654321', 'Học sinh', NOW()),
('student002', '$2b$12$LQv3c1yqBwlVHpPjrCeyAueVuV/1zXtEIYqZe5rBhOwqMLwxo6QN2', 'Trần Thị Bình', 'student002@school.edu.vn', '0987654322', 'Học sinh', NOW()),
('teacher001', '$2b$12$LQv3c1yqBwlVHpPjrCeyAueVuV/1zXtEIYqZe5rBhOwqMLwxo6QN2', 'TS. Lê Văn Cường', 'teacher001@school.edu.vn', '0987654323', 'Giáo viên', NOW()),
('teacher002', '$2b$12$LQv3c1yqBwlVHpPjrCeyAueVuV/1zXtEIYqZe5rBhOwqMLwxo6QN2', 'PGS. Phạm Thị Dung', 'teacher002@school.edu.vn', '0987654324', 'Giáo viên', NOW());

-- Sample Students
INSERT INTO students (UserID, StudentCode, DateOfBirth, Major, EnrollmentDate) VALUES
(2, 'SV001', '2000-05-15', 'Công nghệ thông tin', '2020-09-01'),
(3, 'SV002', '2001-08-20', 'Kế toán', '2021-09-01');

-- Sample Teachers
INSERT INTO teachers (UserID, TeacherCode, Department, HireDate) VALUES
(4, 'GV001', 'Khoa Công nghệ thông tin', '2015-09-01'),
(5, 'GV002', 'Khoa Kinh tế', '2018-09-01');

-- Sample Courses
INSERT INTO courses (CourseCode, CourseName, Credits, Description) VALUES
('IT101', 'Nhập môn Lập trình', 3, 'Khóa học giới thiệu các khái niệm cơ bản về lập trình'),
('IT201', 'Cấu trúc dữ liệu và Giải thuật', 4, 'Khóa học về cấu trúc dữ liệu và các giải thuật cơ bản'),
('IT301', 'Cơ sở dữ liệu', 3, 'Khóa học về thiết kế và quản lý cơ sở dữ liệu'),
('ACC101', 'Nguyên lý Kế toán', 3, 'Khóa học về các nguyên lý cơ bản của kế toán'),
('ACC201', 'Kế toán Tài chính', 4, 'Khóa học về kế toán tài chính doanh nghiệp');

-- Sample Classes
INSERT INTO classes (CourseID, TeacherID, Semester, AcademicYear, MaxCapacity, CurrentEnrollment, Status) VALUES
(1, 1, 'Học kỳ 1', '2024-2025', 40, 2, 'Mở'),
(2, 1, 'Học kỳ 1', '2024-2025', 35, 1, 'Mở'),
(3, 1, 'Học kỳ 2', '2024-2025', 30, 0, 'Mở'),
(4, 2, 'Học kỳ 1', '2024-2025', 45, 1, 'Mở'),
(5, 2, 'Học kỳ 2', '2024-2025', 40, 0, 'Mở');

-- Sample Schedules
INSERT INTO schedules (ClassID, DayOfWeek, StartTime, EndTime, RoomLocation) VALUES
(1, 'Thứ Hai', '08:00:00', '10:30:00', 'Phòng A101'),
(1, 'Thứ Tư', '08:00:00', '10:30:00', 'Phòng A101'),
(2, 'Thứ Ba', '13:30:00', '16:00:00', 'Phòng B201'),
(2, 'Thứ Năm', '13:30:00', '16:00:00', 'Phòng B201'),
(3, 'Thứ Sáu', '08:00:00', '10:30:00', 'Phòng C301'),
(4, 'Thứ Hai', '13:30:00', '16:00:00', 'Phòng D401'),
(4, 'Thứ Tư', '13:30:00', '16:00:00', 'Phòng D401'),
(5, 'Thứ Ba', '08:00:00', '10:30:00', 'Phòng E501');

-- Sample Enrollments
INSERT INTO enrollments (StudentID, ClassID, EnrollmentDate, Status) VALUES
(1, 1, NOW(), 'Đã đăng ký'),
(1, 2, NOW(), 'Đã đăng ký'),
(2, 1, NOW(), 'Đã đăng ký'),
(2, 4, NOW(), 'Đã đăng ký');