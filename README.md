# Hệ Thống Quản Lý Trường Học API

Hệ thống quản lý trường học với xác thực JWT, phân quyền người dùng, và các tính năng quản lý học vụ nâng cao.

## Tính năng chính

### 🔐 Xác thực và Phân quyền

- **JWT Authentication**: Sử dụng Access Token (hết hạn sau 1 giờ) và Refresh Token (hết hạn sau 30 ngày).
- **Phân quyền**: 3 vai trò người dùng: **Học sinh**, **Giáo viên**, và **Cán bộ quản lý**.
- **Token Blacklist**: Quản lý token hết hạn hoặc đăng xuất bằng Redis.
- **Bảo mật mật khẩu**: Mã hóa mật khẩu bằng bcrypt với salt ngẫu nhiên.

### 👨‍🎓 Chức năng cho Học sinh

- **Xem thông báo chung**: Nhận thông báo từ hệ thống.
- **Xem lịch học cá nhân**: Kiểm tra lịch học theo lớp đã đăng ký.
- **Đăng ký học phần**: Đăng ký lớp học mở trong kỳ học.
- **Xem danh sách lớp có thể đăng ký**: Lọc các lớp học phù hợp với điều kiện.

### 👨‍🏫 Chức năng cho Giáo viên

- **Xem lịch dạy cá nhân**: Xem lịch giảng dạy theo lớp được phân công.
- **Xem thông báo giáo viên**: Nhận thông báo dành riêng cho giáo viên.
- **Xem thông tin sinh viên**: Kiểm tra danh sách sinh viên trong các lớp.
- **Xem danh sách học phần**: Xem các khóa học được phân công giảng dạy.

### 👨‍💼 Chức năng cho Cán bộ quản lý

- **Thống kê tổng quan**: Xem số liệu tổng quan về hệ thống (số lượng người dùng, lớp học, v.v.).
- **Quản lý lớp học**:
  - **Tạo lớp học mới**: Thêm lớp học với thông tin khóa học, học kỳ, năm học, sức chứa, ngày bắt đầu và ngày kết thúc.
  - **Cập nhật lớp học**: Chỉnh sửa thông tin lớp học (trừ `course_id` và các ràng buộc trạng thái).
- **Quản lý người dùng**:
  - **Thêm/Cập nhật sinh viên**: Thêm hoặc chỉnh sửa thông tin sinh viên (tên, email, số điện thoại, ngành học, v.v.).
  - **Thêm/Cập nhật giáo viên**: Thêm hoặc chỉnh sửa thông tin giáo viên (tên, email, số điện thoại, khoa, v.v.).
- **Phân công giáo viên**: Gán giáo viên cho các lớp học.
- **Quản lý toàn bộ dữ liệu**: Xem và quản lý tất cả người dùng, lớp học, và khóa học.

## Công nghệ sử dụng

- **Backend**: Flask, Python 3.11
- **Database**: MySQL 8.0
- **Cache**: Redis 7
- **Authentication**: Flask-JWT-Extended
- **ORM**: Flask-SQLAlchemy
- **Migration**: Flask-Migrate (dựa trên Alembic)
- **Containerization**: Docker, Docker Compose
- **CORS**: Flask-CORS cho hỗ trợ cross-origin requests

## Cài đặt và Chạy

### 1. Clone repository

```bash
git clone https://github.com/chuong1210/School-Management-System.git
cd school-management-system
```

### 2. Cấu hình môi trường

Sao chép file mẫu `.env` và chỉnh sửa các biến môi trường:

```bash
cp .env.example .env
# Chỉnh sửa .env với các thông tin cấu hình của bạn
```

Nội dung file `.env` ví dụ:

```bash
# Database Configuration
MYSQL_ROOT_PASSWORD=101204
MYSQL_DATABASE=school_management
MYSQL_USER=myuser
MYSQL_PASSWORD=101204

# Flask Configuration
SECRET_KEY=123456jjj
JWT_SECRET_KEY=678910jjj
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000

# Database URL
DATABASE_URL=mysql+pymysql://myuser:101204@db:3306/school_management
REDIS_URL=redis://redis:6379/0

# Flask Settings
FLASK_ENV=development
FLASK_DEBUG=1
```

### 3. Chạy với Docker Compose

```bash
docker-compose up --build -d
```

### 4. Áp dụng Database Migration

Sau khi khởi động các container, áp dụng migration để cập nhật schema (bao gồm `StartDate` và `EndDate`):

```bash
docker exec -it api-web-1 bash
flask db init  # Chỉ chạy lần đầu
flask db migrate -m "Add start_date and end_date to classes table"
flask db upgrade
```

### 5. Kiểm tra kết nối

```bash
curl http://localhost:5000/health
```

**Kết quả mong đợi**:

```json
{
  "status": "healthy",
  "services": {
    "flask": "running",
    "mysql": "connected",
    "redis": "connected"
  }
}
```

## API Endpoints

### Authentication

- `POST /api/auth/register` - Đăng ký tài khoản mới.
- `POST /api/auth/login` - Đăng nhập và nhận JWT token.
- `POST /api/auth/refresh` - Làm mới access token bằng refresh token.
- `POST /api/auth/logout` - Đăng xuất và đưa token vào blacklist.
- `GET /api/auth/profile` - Xem thông tin cá nhân của người dùng hiện tại.

### Student Endpoints

- `GET /api/student/notifications` - Xem danh sách thông báo.
- `GET /api/student/schedule` - Xem lịch học cá nhân.
- `POST /api/student/enroll` - Đăng ký học phần.
- `GET /api/student/available-classes` - Xem danh sách lớp học có thể đăng ký.

### Teacher Endpoints

- `GET /api/teacher/teaching-schedule` - Xem lịch giảng dạy.
- `GET /api/teacher/notifications` - Xem thông báo dành cho giáo viên.
- `GET /api/teacher/students` - Xem danh sách sinh viên trong lớp.
- `GET /api/teacher/courses` - Xem danh sách khóa học được phân công.

### Manager Endpoints

- `GET /api/manager/overview` - Xem thống kê tổng quan hệ thống.
- `POST /api/manager/create-class` - Tạo lớp học mới với thông tin ngày bắt đầu và ngày kết thúc.
- `PUT /api/manager/update-class/<int:class_id>` - Cập nhật thông tin lớp học.
- `POST /api/manager/add-student` - Thêm sinh viên mới.
- `PUT /api/manager/update-student/<int:student_id>` - Cập nhật thông tin sinh viên.
- `POST /api/manager/add-teacher` - Thêm giáo viên mới.
- `PUT /api/manager/update-teacher/<int:teacher_id>` - Cập nhật thông tin giáo viên.
- `POST /api/manager/assign-teacher` - Phân công giáo viên cho lớp học.
- `GET /api/manager/all-users` - Xem danh sách tất cả người dùng.
- `GET /api/manager/all-classes` - Xem danh sách tất cả lớp học.

## Cấu trúc Database

### Bảng `users`

- Lưu thông tin cơ bản của tất cả người dùng.
- Các trường: `UserID`, `Username` (unique), `Password` (bcrypt hash), `FullName`, `Email` (unique), `PhoneNumber`, `UserType` (Quản lý/Giáo viên/Học sinh), `DateCreated`, `LastLogin`.

### Bảng `students` / `teachers`

- Lưu thông tin chi tiết của sinh viên và giáo viên.
- Liên kết với `users` qua `UserID` (foreign key).
- `students`: `StudentID`, `StudentCode`, `DateOfBirth`, `Major`, `EnrollmentDate`.
- `teachers`: `TeacherID`, `TeacherCode`, `Department`, `HireDate`.

### Bảng `courses` / `classes`

- `courses`: Lưu thông tin khóa học (`CourseID`, `CourseCode`, `CourseName`, `Credits`, `Description`).
- `classes`: Quản lý lớp học (`ClassID`, `CourseID`, `TeacherID`, `Semester`, `AcademicYear`, `MaxCapacity`, `CurrentEnrollment`, `Status`, `StartDate`, `EndDate`).
- `StartDate` và `EndDate` được thêm để theo dõi thời gian diễn ra lớp học.

### Bảng `schedules` / `enrollments`

- `schedules`: Lưu lịch học của các lớp.
- `enrollments`: Quản lý đăng ký học phần, với ràng buộc unique để tránh đăng ký trùng.

## Tài khoản mẫu

Hệ thống khởi tạo các tài khoản mẫu với mật khẩu: `123456` (đã mã hóa bằng bcrypt):

### Cán bộ quản lý

- Username: `admin`
- Password: `123456`

### Học sinh

- Username: `student001`, `student002`
- Password: `123456`

### Giáo viên

- Username: `teacher001`, `teacher002`
- Password: `123456`

## Ví dụ sử dụng API

### 1. Đăng nhập

```bash
curl -X POST https://ai-api.bitech.vn/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "123456"
  }'
```

**Kết quả**:

```json
{
  "success": true,
  "message": "Đăng nhập thành công.",
  "timestamp": "2025-08-08T12:34:00.123456",
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
```

### 2. Tạo lớp học mới (Cán bộ quản lý)

```bash
curl -X POST https://ai-api.bitech.vn/api/manager/create-class \
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
```

**Kết quả**:

```json
{
  "success": true,
  "message": "Tạo lớp học thành công.",
  "timestamp": "2025-08-08T12:34:00.123456",
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
        "credits": 3,
        "description": "Khóa học giới thiệu các khái niệm cơ bản về lập trình"
      }
    }
  }
}
```

### 3. Thêm sinh viên mới (Cán bộ quản lý)

```bash
curl -X POST https://ai-api.bitech.vn/api/manager/add-student \
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
```

**Kết quả**:

```json
{
  "success": true,
  "message": "Thêm sinh viên thành công.",
  "timestamp": "2025-08-08T12:34:00.123456",
  "status_code": 201,
  "data": {
    "user": {
      "user_id": 3,
      "username": "student003",
      "full_name": "Phạm Văn Cường",
      "email": "student003@school.edu.vn",
      "phone_number": "0987654325",
      "user_type": "Học sinh",
      "student_info": {
        "student_id": 3,
        "user_id": 3,
        "major": "Kỹ thuật phần mềm"
      }
    }
  }
}
```

### 4. Cập nhật lớp học (Cán bộ quản lý)

```bash
curl -X PUT https://ai-api.bitech.vn/api/manager/update-class/1 \
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
```

**Kết quả**:

```json
{
  "success": true,
  "message": "Cập nhật lớp học thành công.",
  "timestamp": "2025-08-08T12:34:00.123456",
  "status_code": 200,
  "data": {
    "class": {
      "class_id": 1,
      "course_id": 1,
      "teacher_id": null,
      "semester": "Học kỳ 1",
      "academic_year": "2025-2026",
      "max_capacity": 50,
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
```

## Bảo mật

### JWT Token Security

- **Access Token**: Hết hạn sau 1 giờ.
- **Refresh Token**: Hết hạn sau 30 ngày.
- **Token Blacklist**: Lưu trữ trong Redis để vô hiệu hóa token khi đăng xuất.
- **CORS**: Cấu hình cho phép các domain cụ thể (e.g., `https://ai-api.bitech.vn`).

### Password Security

- Mã hóa mật khẩu bằng bcrypt với salt ngẫu nhiên.
- Không lưu trữ mật khẩu dạng plain text.
- Kiểm tra độ mạnh của mật khẩu khi đăng ký (khuyến nghị).

### Database Security

- Sử dụng Flask-SQLAlchemy để tránh SQL injection.
- Ràng buộc foreign key và unique constraints để đảm bảo tính toàn vẹn dữ liệu.
- Migration với Flask-Migrate để quản lý thay đổi schema.

## Monitoring và Logging

### Health Check

```bash
curl https://ai-api.bitech.vn/health
```

### Container Logs

```bash
docker-compose logs -f web
docker-compose logs -f db
docker-compose logs -f redis
```

## Development

### Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### Chạy development server

```bash
export FLASK_ENV=development
python app.py
```

### Database Migration

```bash
# Tạo migration
flask db migrate -m "Description"

# Áp dụng migration
flask db upgrade

# Hoàn tác migration (nếu cần)
flask db downgrade
```

## Production Deployment

### Environment Variables

```bash
FLASK_ENV=production
SECRET_KEY=your-production-secret-key
JWT_SECRET_KEY=your-production-jwt-secret
DATABASE_URL=mysql+pymysql://user:pass@host:port/db
REDIS_URL=redis://redis-host:6379/0
```

### Docker Production

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Deployed Endpoint

API hiện đang chạy tại: `https://ai-api.bitech.vn`.

## Troubleshooting

### Common Issues

1. **Database Connection Error**

   ```bash
   # Kiểm tra trạng thái container
   docker-compose ps

   # Xem log database
   docker-compose logs db
   ```

2. **Redis Connection Error**

   ```bash
   # Kiểm tra container Redis
   docker-compose ps redis

   # Kiểm tra kết nối Redis
   docker-compose exec redis redis-cli ping
   ```

3. **JWT Token Issues**

   ```bash
   # Xóa cache Redis
   docker-compose exec redis redis-cli FLUSHALL
   ```

4. **405 Method Not Allowed**

   - Kiểm tra phương thức HTTP (`POST`, `GET`, `PUT`, v.v.) trong request.
   - Đảm bảo endpoint hỗ trợ phương thức được sử dụng.

### Performance Tuning

1. **Database Indexing**

   - Tạo index cho các trường thường xuyên truy vấn: `username`, `email`, `user_type`.
   - Index cho foreign keys: `user_id`, `course_id`, `class_id`.

2. **Redis Optimization**

   - Cấu hình giới hạn bộ nhớ Redis.
   - Sử dụng Redis clustering cho môi trường production.

3. **Application Optimization**

   - Sử dụng connection pooling cho database.
   - Thêm caching cho các truy vấn thường xuyên.
   - Triển khai pagination cho các endpoint trả về nhiều dữ liệu.

## Contributing

1. Fork repository.
2. Tạo feature branch: `git checkout -b feature/AmazingFeature`.
3. Commit changes: `git commit -m 'Add some AmazingFeature'`.
4. Push to branch: `git push origin feature/AmazingFeature`.
5. Tạo Pull Request trên GitHub.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

Nếu gặp vấn đề hoặc có câu hỏi, vui lòng tạo issue trên [GitHub repository](https://github.com/chuong1210/School-Management-System).