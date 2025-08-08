School Management System API
Hệ thống quản lý trường học với JWT authentication và phân quyền người dùng.
Tính năng chính
🔐 Xác thực và Phân quyền

JWT Access Token và Refresh Token
3 loại người dùng: Học sinh, Giáo viên, Cán bộ quản lý
Token blacklist với Redis
Bảo mật mật khẩu với bcrypt

👨‍🎓 Chức năng cho Học sinh

Xem thông báo chung
Xem lịch học cá nhân
Đăng ký học phần
Xem danh sách lớp có thể đăng ký

👨‍🏫 Chức năng cho Giáo viên

Xem lịch dạy cá nhân
Xem thông báo dành cho giáo viên
Xem thông tin sinh viên trong lớp
Xem danh sách học phần được phân công

👨‍💼 Chức năng cho Cán bộ quản lý

Xem thống kê tổng quan hệ thống
Tạo lớp học mới với thông tin ngày bắt đầu và kết thúc
Cập nhật thông tin lớp học (trừ ID khóa học)
Thêm và cập nhật thông tin sinh viên
Thêm và cập nhật thông tin giáo viên
Phân công giáo viên cho lớp
Quản lý tất cả người dùng và lớp học

Công nghệ sử dụng

Backend: Flask, Python 3.11
Database: MySQL 8.0
Cache: Redis 7
Authentication: JWT (Flask-JWT-Extended)
ORM: SQLAlchemy
Migration: Flask-Migrate (Alembic)
Containerization: Docker, Docker Compose

Cài đặt và Chạy
1. Clone repository
git clone https://github.com/chuong1210/School-Management-System.git
cd school-management-system

2. Cấu hình môi trường
cp .env.example .env
# Edit .env file with your configurations

Mẫu .env:
FLASK_ENV=development
SECRET_KEY=123456jjj
JWT_SECRET_KEY=678910jjj
DATABASE_URL=mysql+pymysql://myuser:101204@db:3306/school_management
REDIS_URL=redis://redis:6379/0
MYSQL_ROOT_PASSWORD=101204
MYSQL_DATABASE=school_management
MYSQL_USER=myuser
MYSQL_PASSWORD=101204

3. Chạy với Docker Compose
docker-compose up --build -d

4. Áp dụng Database Migration
docker exec -it api-web-1 bash
flask db init  # Chỉ chạy lần đầu
flask db migrate -m "Initial migration"
flask db upgrade

5. Kiểm tra kết nối
curl http://localhost:5000/health

API Endpoints
Authentication

POST /api/auth/register - Đăng ký tài khoản
POST /api/auth/login - Đăng nhập
POST /api/auth/refresh - Làm mới access token
POST /api/auth/logout - Đăng xuất
GET /api/auth/profile - Xem thông tin cá nhân

Student Endpoints

GET /api/student/notifications - Xem thông báo
GET /api/student/schedule - Xem lịch học
POST /api/student/enroll - Đăng ký học phần
GET /api/student/available-classes - Xem lớp có thể đăng ký

Teacher Endpoints

GET /api/teacher/teaching-schedule - Xem lịch dạy
GET /api/teacher/notifications - Xem thông báo giáo viên
GET /api/teacher/students - Xem danh sách sinh viên
GET /api/teacher/courses - Xem các khóa học được phân công

Manager Endpoints

GET /api/manager/overview - Xem thống kê tổng quan
POST /api/manager/create-class - Tạo lớp học mới
PUT /api/manager/update-class/<class_id> - Cập nhật thông tin lớp học
POST /api/manager/add-student - Thêm sinh viên mới
PUT /api/manager/update-student/<student_id> - Cập nhật thông tin sinh viên
POST /api/manager/add-teacher - Thêm giáo viên mới
PUT /api/manager/update-teacher/<teacher_id> - Cập nhật thông tin giáo viên
POST /api/manager/assign-teacher - Phân công giáo viên
GET /api/manager/all-users - Xem tất cả người dùng
GET /api/manager/all-classes - Xem tất cả lớp học

Cấu trúc Database
Bảng Users

UserID (PK, auto-increment)
Username (unique, not null)
Password (bcrypt hashed, not null)
FullName (not null)
Email (unique, not null)
PhoneNumber
UserType (ENUM: 'Quản lý', 'Giáo viên', 'Học sinh')
DateCreated (default: CURRENT_TIMESTAMP)
LastLogin

Bảng Students

StudentID (PK, auto-increment)
UserID (FK, unique, references Users)
StudentCode
DateOfBirth
Major
EnrollmentDate

Bảng Teachers

TeacherID (PK, auto-increment)
UserID (FK, unique, references Users)
TeacherCode
Department
HireDate

Bảng Courses

CourseID (PK, auto-increment)
CourseCode (not null)
CourseName (not null)
Credits (not null)
Description

Bảng Classes

ClassID (PK, auto-increment)
CourseID (FK, references Courses)
TeacherID (FK, references Teachers, nullable)
Semester (not null)
AcademicYear (not null)
MaxCapacity (not null)
CurrentEnrollment (default: 0)
Status (not null)
StartDate (not null)
EndDate (not null)

Bảng Schedules / Enrollments

Lịch học và đăng ký học phần
Ràng buộc unique để tránh đăng ký trùng

Tài khoản mẫu
Hệ thống tạo sẵn các tài khoản mẫu (password: 123456):
Cán bộ quản lý

Username: admin
Password: 123456

Học sinh

Username: student001, student002
Password: 123456

Giáo viên

Username: teacher001, teacher002
Password: 123456

Ví dụ sử dụng API
1. Đăng nhập
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "123456"
  }'

Response:
{
  "success": true,
  "message": "Đăng nhập thành công.",
  "timestamp": "2025-08-08T12:29:00.123456",
  "status_code": 200,
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ...",
    "user": {
      "user_id": 1,
      "username": "admin",
      "full_name": "Admin User",
      "email": "admin@school.edu.vn",
      "phone_number": "0123456789",
      "user_type": "Quản lý"
    }
  }
}

2. Tạo lớp học mới (Cán bộ quản lý)
curl -X POST http://localhost:5000/api/manager/create-class \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": 1,
    "semester": "Học kỳ 1",
    "academic_year": "2025-2026",
    "max_capacity": 40,
    "start_date": "2025-09-01",
    "end_date": "2025-12-31"
  }'

Response:
{
  "success": true,
  "message": "Tạo lớp học thành công.",
  "timestamp": "2025-08-08T12:29:00.123456",
  "status_code": 201,
  "data": {
    "class": {
      "class_id": 1,
      "course_id": 1,
      "teacher_id": null,
      "semester": "Học kỳ 1",
      "academic_year": "2025-2026",
      "max_capacity": 40,
      "current_enrollment": 0,
      "status": "Mở",
      "start_date": "2025-09-01",
      "end_date": "2025-12-31",
      "course_info": {
        "course_id": 1,
        "course_code": "IT101",
        "course_name": "Nhập môn Lập trình",
        "credits": 3
      }
    }
  }
}

3. Cập nhật lớp học (Cán bộ quản lý)
curl -X PUT http://localhost:5000/api/manager/update-class/1 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "semester": "Học kỳ 1",
    "academic_year": "2025-2026",
    "max_capacity": 50,
    "start_date": "2025-09-01",
    "end_date": "2025-12-31",
    "status": "Mở"
  }'

4. Thêm sinh viên mới (Cán bộ quản lý)
curl -X POST http://localhost:5000/api/manager/add-student \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student003",
    "password": "password123",
    "full_name": "Phạm Văn Cường",
    "email": "student003@school.edu.vn",
    "phone_number": "0987654325",
    "major": "Kỹ thuật phần mềm"
  }'

5. Thêm giáo viên mới (Cán bộ quản lý)
curl -X POST http://localhost:5000/api/manager/add-teacher \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "teacher003",
    "password": "password123",
    "full_name": "Nguyễn Thị Hồng",
    "email": "teacher003@school.edu.vn",
    "phone_number": "0987654326",
    "department": "Khoa Toán học"
  }'

Bảo mật
JWT Token Security

Access token hết hạn sau 1 giờ
Refresh token hết hạn sau 30 ngày
Token blacklist với Redis khi đăng xuất
CORS được cấu hình cho frontend

Password Security

Mã hóa với bcrypt và salt
Không lưu mật khẩu dạng plain text
Validation mật khẩu mạnh (khuyến nghị)

Database Security

Sử dụng ORM để tránh SQL injection
Foreign key constraints
Unique constraints cho business logic
Non-nullable StartDate và EndDate trong bảng Classes

Monitoring và Logging
Health Check
curl http://localhost:5000/health

Container Logs
docker-compose logs -f web
docker-compose logs -f db
docker-compose logs -f redis

Development
Cài đặt dependencies
pip install -r requirements.txt

Chạy development server
export FLASK_ENV=development
python app.py

Database Migration
# Tạo migration
flask db migrate -m "Add start_date and end_date to classes"

# Áp dụng migration
flask db upgrade

Production Deployment
Environment Variables
FLASK_ENV=production
SECRET_KEY=your-production-secret-key
JWT_SECRET_KEY=your-production-jwt-secret
DATABASE_URL=mysql+pymysql://user:pass@host:port/db
REDIS_URL=redis://redis-host:6379/0

Docker Production
docker-compose -f docker-compose.prod.yml up -d

Deployed Endpoint

API hiện đang chạy tại: https://ai-api.bitech.vn

Troubleshooting
Common Issues

Database Connection Error
# Kiểm tra trạng thái container
docker-compose ps

# Kiểm tra logs database
docker-compose logs db


Redis Connection Error
# Kiểm tra Redis container
docker-compose ps redis

# Kiểm tra kết nối Redis
docker-compose exec redis redis-cli ping


JWT Token Issues
# Xóa Redis cache
docker-compose exec redis redis-cli FLUSHALL


init.sql Errors

Kiểm tra init.sql có cú pháp hợp lệ
Chuyển line endings sang Unix (LF) nếu dùng Windows:dos2unix init.sql





Performance Tuning

Database Indexing

Index trên: username, email, user_type, course_id, class_id
Index trên foreign keys: user_id, course_id, teacher_id


Redis Optimization

Cấu hình memory limit
Sử dụng Redis clustering cho production


Application Optimization

Database connection pooling
Caching cho query thường xuyên
Pagination cho endpoint trả nhiều dữ liệu



Contributing

Fork repository
Tạo feature branch (git checkout -b feature/AmazingFeature)
Commit changes (git commit -m 'Add some AmazingFeature')
Push to branch (git push origin feature/AmazingFeature)
Tạo Pull Request

License
This project is licensed under the MIT License - see the LICENSE file for details.
Support
Nếu có vấn đề hoặc câu hỏi, vui lòng tạo issue trên GitHub repository.
