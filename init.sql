
SET NAMES UTF8MB4;
SET CHARACTER SET utf8mb4;
CREATE DATABASE IF NOT EXISTS school_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE school_management;


-- Insert sample data

-- Create tables
CREATE TABLE courses (
    CourseID INT PRIMARY KEY AUTO_INCREMENT,
    CourseCode VARCHAR(50) NOT NULL,
    CourseName VARCHAR(255) NOT NULL,
    Credits INT NOT NULL,
    Description TEXT
);

CREATE TABLE users (
    UserID INT PRIMARY KEY AUTO_INCREMENT,
    Username VARCHAR(50) UNIQUE NOT NULL,
    PasswordHash VARCHAR(255) NOT NULL,
    FullName VARCHAR(255) NOT NULL,
    Email VARCHAR(255) UNIQUE NOT NULL,
    PhoneNumber VARCHAR(20),
    UserType ENUM('Cán bộ quản lý', 'Giáo viên', 'Học sinh') NOT NULL,
    DateCreated DATETIME DEFAULT CURRENT_TIMESTAMP,
    LastLogin DATETIME
);
ALTER TABLE users CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE students (
    StudentID INT PRIMARY KEY AUTO_INCREMENT,
    UserID INT UNIQUE NOT NULL,
    StudentCode VARCHAR(50),
    DateOfBirth DATE,
    Major VARCHAR(255),
    EnrollmentDate DATE,
    FOREIGN KEY (UserID) REFERENCES users(UserID)
);

CREATE TABLE teachers (
    TeacherID INT PRIMARY KEY AUTO_INCREMENT,
    UserID INT UNIQUE NOT NULL,
    TeacherCode VARCHAR(50),
    Department VARCHAR(255),
    HireDate DATE,
    FOREIGN KEY (UserID) REFERENCES users(UserID)
);

CREATE TABLE classes (
    ClassID INT PRIMARY KEY AUTO_INCREMENT,
    CourseID INT NOT NULL,
    TeacherID INT,
    Semester VARCHAR(50) NOT NULL,
    AcademicYear VARCHAR(10) NOT NULL,
    MaxCapacity INT,
    CurrentEnrollment INT DEFAULT 0,
    Status VARCHAR(20) NOT NULL,
    StartDate DATE NOT NULL,
    EndDate DATE NOT NULL,
    FOREIGN KEY (CourseID) REFERENCES courses(CourseID),
    FOREIGN KEY (TeacherID) REFERENCES teachers(TeacherID)
);
CREATE TABLE IF NOT EXISTS schedules (
    ScheduleID INT AUTO_INCREMENT PRIMARY KEY,
    ClassID INT NOT NULL,
    DayOfWeek VARCHAR(50) NOT NULL,
    StartTime TIME NOT NULL,
    EndTime TIME NOT NULL,
    RoomLocation VARCHAR(100),
    FOREIGN KEY (ClassID) REFERENCES classes(ClassID)
);

CREATE TABLE IF NOT EXISTS enrollments (
    EnrollmentID  INT AUTO_INCREMENT PRIMARY KEY,
    StudentID INT,
    ClassID INT,
    EnrollmentDate DATETIME,
    Status VARCHAR(20),
    Grade VARCHAR(6),
    
    FOREIGN KEY (StudentID) REFERENCES students(StudentID),
    FOREIGN KEY (ClassID) REFERENCES classes(ClassID)
);
-- Insert sample data
-- Sample Users
INSERT INTO users (Username, PasswordHash, FullName, Email, PhoneNumber, UserType, DateCreated) VALUES
('admin', '$2a$10$OhDj1ffutzBH934vRc34y.LqXckQxGN7n1po5qR1wbWVycBNf/Dxq', 'Quản trị viên hệ thống', 'admin@school.edu.vn', '0123456789', 'Cán bộ quản lý', NOW()),
('student001', '$2a$10$OhDj1ffutzBH934vRc34y.LqXckQxGN7n1po5qR1wbWVycBNf/Dxq', 'Nguyễn Văn An', 'student001@school.edu.vn', '0987654321', 'Học sinh', NOW()),
('student002', '$2a$10$OhDj1ffutzBH934vRc34y.LqXckQxGN7n1po5qR1wbWVycBNf/Dxq', 'Trần Thị Bình', 'student002@school.edu.vn', '0987654322', 'Học sinh', NOW()),
('teacher001', '$2a$10$OhDj1ffutzBH934vRc34y.LqXckQxGN7n1po5qR1wbWVycBNf/Dxq', 'TS. Lê Văn Cường', 'teacher001@school.edu.vn', '0987654323', 'Giáo viên', NOW()),
('teacher002', '$2a$10$OhDj1ffutzBH934vRc34y.LqXckQxGN7n1po5qR1wbWVycBNf/Dxq', 'PGS. Phạm Thị Dung', 'teacher002@school.edu.vn', '0987654324', 'Giáo viên', NOW());

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
INSERT INTO classes 
(CourseID, TeacherID, Semester, AcademicYear, MaxCapacity, CurrentEnrollment, Status, StartDate, EndDate) 
VALUES
(1, 1, 'Học kỳ 1', '2024-2025', 40, 2, 'Mở', '2024-09-01', '2025-01-15'),
(2, 1, 'Học kỳ 1', '2024-2025', 35, 1, 'Mở', '2024-09-01', '2025-01-15'),
(3, 1, 'Học kỳ 2', '2024-2025', 30, 0, 'Mở', '2025-02-01', '2025-06-01'),
(4, 2, 'Học kỳ 1', '2024-2025', 45, 1, 'Mở', '2024-09-01', '2025-01-15'),
(5, 2, 'Học kỳ 2', '2024-2025', 40, 0, 'Mở', '2025-02-01', '2025-06-01');

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