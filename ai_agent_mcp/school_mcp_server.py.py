import asyncio
import json
import logging
import os
import aiohttp
from typing import Dict, Any, Optional

import mcp.server.stdio
from dotenv import load_dotenv

# ADK Tool Imports
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

# MCP Server Imports
from mcp import types as mcp_types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

load_dotenv()

# --- Logging Setup ---
LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), "school_mcp_server_activity.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, mode="w"),
    ],
)

# API Configuration
API_BASE_URL = "https://ai-api.bitech.vn/api"
ACCESS_TOKEN = None

# --- API Helper Functions ---
async def make_api_request(method: str, endpoint: str, data: Dict = None, auth_required: bool = True) -> Dict[str, Any]:
    """Thực hiện HTTP request đến API."""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    if auth_required and ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
    
    async with aiohttp.ClientSession() as session:
        try:
            if method.upper() == "GET":
                async with session.get(url, headers=headers) as response:
                    result = await response.json()
                    return result
            elif method.upper() == "POST":
                async with session.post(url, headers=headers, json=data) as response:
                    result = await response.json()
                    return result
            elif method.upper() == "PUT":
                async with session.put(url, headers=headers, json=data) as response:
                    result = await response.json()
                    return result
        except Exception as e:
            return {"success": False, "message": f"Lỗi kết nối API: {str(e)}"}

# --- Authentication Functions ---
async def login(username: str, password: str) -> Dict[str, Any]:
    """Đăng nhập vào hệ thống."""
    global ACCESS_TOKEN
    
    login_data = {
        "username": username,
        "password": password
    }
    
    result = await make_api_request("POST", "/auth/login", login_data, auth_required=False)
    
    if result.get("success"):
        ACCESS_TOKEN = result["data"]["access_token"]
        return {
            "success": True,
            "message": "Đăng nhập thành công",
            "user_info": result["data"]["user"]
        }
    
    return result

async def logout() -> Dict[str, Any]:
    """Đăng xuất khỏi hệ thống."""
    global ACCESS_TOKEN
    
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Chưa đăng nhập"}
    
    result = await make_api_request("POST", "/auth/logout")
    ACCESS_TOKEN = None
    
    return result if result else {"success": True, "message": "Đăng xuất thành công"}

async def get_profile() -> Dict[str, Any]:
    """Xem thông tin cá nhân."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    return await make_api_request("GET", "/auth/profile")

# --- Student Functions ---
async def get_student_notifications() -> Dict[str, Any]:
    """Xem thông báo dành cho học sinh."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    return await make_api_request("GET", "/student/notifications")

async def get_student_schedule() -> Dict[str, Any]:
    """Xem lịch học cá nhân của học sinh."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    return await make_api_request("GET", "/student/schedule")

async def enroll_class(class_id: int) -> Dict[str, Any]:
    """Đăng ký lớp học."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    enroll_data = {"class_id": class_id}
    return await make_api_request("POST", "/student/enroll", enroll_data)

async def get_available_classes() -> Dict[str, Any]:
    """Xem danh sách lớp học có thể đăng ký."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    return await make_api_request("GET", "/student/available-classes")

# --- Teacher Functions ---
async def get_teaching_schedule() -> Dict[str, Any]:
    """Xem lịch giảng dạy của giáo viên."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    return await make_api_request("GET", "/teacher/teaching-schedule")

async def get_teacher_notifications() -> Dict[str, Any]:
    """Xem thông báo dành cho giáo viên."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    return await make_api_request("GET", "/teacher/notifications")

async def get_teacher_students() -> Dict[str, Any]:
    """Xem danh sách sinh viên trong lớp."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    return await make_api_request("GET", "/teacher/students")

async def get_teacher_courses() -> Dict[str, Any]:
    """Xem danh sách khóa học được phân công."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    return await make_api_request("GET", "/teacher/courses")

# --- Manager Functions ---
async def get_system_overview() -> Dict[str, Any]:
    """Xem thống kê tổng quan hệ thống."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    return await make_api_request("GET", "/manager/overview")

async def create_class(course_id: int, semester: str, academic_year: str, 
                      max_capacity: int, start_date: str, end_date: str) -> Dict[str, Any]:
    """Tạo lớp học mới."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    class_data = {
        "course_id": course_id,
        "semester": semester,
        "academic_year": academic_year,
        "max_capacity": max_capacity,
        "start_date": start_date,
        "end_date": end_date
    }
    
    return await make_api_request("POST", "/manager/create-class", class_data)

async def update_class(class_id: int, semester: str = None, academic_year: str = None,
                      max_capacity: int = None, start_date: str = None, 
                      end_date: str = None, status: str = None) -> Dict[str, Any]:
    """Cập nhật thông tin lớp học."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    update_data = {}
    if semester: update_data["semester"] = semester
    if academic_year: update_data["academic_year"] = academic_year
    if max_capacity: update_data["max_capacity"] = max_capacity
    if start_date: update_data["start_date"] = start_date
    if end_date: update_data["end_date"] = end_date
    if status: update_data["status"] = status
    
    return await make_api_request("PUT", f"/manager/update-class/{class_id}", update_data)

async def add_student(username: str, password: str, full_name: str, 
                     email: str, phone_number: str, major: str) -> Dict[str, Any]:
    """Thêm sinh viên mới."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    student_data = {
        "username": username,
        "password": password,
        "full_name": full_name,
        "email": email,
        "phone_number": phone_number,
        "major": major
    }
    
    return await make_api_request("POST", "/manager/add-student", student_data)

async def update_student(student_id: int, full_name: str = None, email: str = None,
                        phone_number: str = None, major: str = None) -> Dict[str, Any]:
    """Cập nhật thông tin sinh viên."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    update_data = {}
    if full_name: update_data["full_name"] = full_name
    if email: update_data["email"] = email
    if phone_number: update_data["phone_number"] = phone_number
    if major: update_data["major"] = major
    
    return await make_api_request("PUT", f"/manager/update-student/{student_id}", update_data)

async def add_teacher(username: str, password: str, full_name: str, 
                     email: str, phone_number: str, department: str) -> Dict[str, Any]:
    """Thêm giáo viên mới."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    teacher_data = {
        "username": username,
        "password": password,
        "full_name": full_name,
        "email": email,
        "phone_number": phone_number,
        "department": department
    }
    
    return await make_api_request("POST", "/manager/add-teacher", teacher_data)

async def update_teacher(teacher_id: int, full_name: str = None, email: str = None,
                        phone_number: str = None, department: str = None) -> Dict[str, Any]:
    """Cập nhật thông tin giáo viên."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    update_data = {}
    if full_name: update_data["full_name"] = full_name
    if email: update_data["email"] = email
    if phone_number: update_data["phone_number"] = phone_number
    if department: update_data["department"] = department
    
    return await make_api_request("PUT", f"/manager/update-teacher/{teacher_id}", update_data)

async def assign_teacher(class_id: int, teacher_id: int) -> Dict[str, Any]:
    """Phân công giáo viên cho lớp học."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    assign_data = {
        "class_id": class_id,
        "teacher_id": teacher_id
    }
    
    return await make_api_request("POST", "/manager/assign-teacher", assign_data)

async def get_all_users() -> Dict[str, Any]:
    """Xem danh sách tất cả người dùng."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    return await make_api_request("GET", "/manager/all-users")

async def get_all_classes() -> Dict[str, Any]:
    """Xem danh sách tất cả lớp học."""
    if not ACCESS_TOKEN:
        return {"success": False, "message": "Vui lòng đăng nhập trước"}
    
    return await make_api_request("GET", "/manager/all-classes")

# --- MCP Server Setup ---
logging.info("Tạo MCP Server cho hệ thống quản lý trường học...")
app = Server("school-management-mcp-server")

# Wrap API functions as ADK FunctionTools
ADK_SCHOOL_TOOLS = {
    # Authentication
    "login": FunctionTool(func=login),
    "logout": FunctionTool(func=logout),
    "get_profile": FunctionTool(func=get_profile),
    
    # Student functions
    "get_student_notifications": FunctionTool(func=get_student_notifications),
    "get_student_schedule": FunctionTool(func=get_student_schedule),
    "enroll_class": FunctionTool(func=enroll_class),
    "get_available_classes": FunctionTool(func=get_available_classes),
    
    # Teacher functions
    "get_teaching_schedule": FunctionTool(func=get_teaching_schedule),
    "get_teacher_notifications": FunctionTool(func=get_teacher_notifications),
    "get_teacher_students": FunctionTool(func=get_teacher_students),
    "get_teacher_courses": FunctionTool(func=get_teacher_courses),
    
    # Manager functions
    "get_system_overview": FunctionTool(func=get_system_overview),
    "create_class": FunctionTool(func=create_class),
    "update_class": FunctionTool(func=update_class),
    "add_student": FunctionTool(func=add_student),
    "update_student": FunctionTool(func=update_student),
    "add_teacher": FunctionTool(func=add_teacher),
    "update_teacher": FunctionTool(func=update_teacher),
    "assign_teacher": FunctionTool(func=assign_teacher),
    "get_all_users": FunctionTool(func=get_all_users),
    "get_all_classes": FunctionTool(func=get_all_classes),
}

@app.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    """MCP handler để liệt kê các công cụ mà server cung cấp."""
    logging.info("MCP Server: Nhận yêu cầu list_tools.")
    mcp_tools_list = []
    for tool_name, adk_tool_instance in ADK_SCHOOL_TOOLS.items():
        if not adk_tool_instance.name:
            adk_tool_instance.name = tool_name

        mcp_tool_schema = adk_to_mcp_tool_type(adk_tool_instance)
        logging.info(
            f"MCP Server: Đăng ký tool: {mcp_tool_schema.name}, InputSchema: {mcp_tool_schema.inputSchema}"
        )
        mcp_tools_list.append(mcp_tool_schema)
    return mcp_tools_list

@app.call_tool()
async def call_mcp_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
    """MCP handler để thực hiện tool call từ MCP client."""
    logging.info(
        f"MCP Server: Nhận yêu cầu call_tool cho '{name}' với args: {arguments}"
    )

    if name in ADK_SCHOOL_TOOLS:
        adk_tool_instance = ADK_SCHOOL_TOOLS[name]
        try:
            adk_tool_response = await adk_tool_instance.run_async(
                args=arguments,
                tool_context=None,
            )
            logging.info(
                f"MCP Server: ADK tool '{name}' thực hiện thành công. Response: {adk_tool_response}"
            )
            response_text = json.dumps(adk_tool_response, indent=2, ensure_ascii=False)
            return [mcp_types.TextContent(type="text", text=response_text)]

        except Exception as e:
            logging.error(
                f"MCP Server: Lỗi khi thực hiện ADK tool '{name}': {e}", exc_info=True
            )
            error_payload = {
                "success": False,
                "message": f"Không thể thực hiện tool '{name}': {str(e)}",
            }
            error_text = json.dumps(error_payload, ensure_ascii=False)
            return [mcp_types.TextContent(type="text", text=error_text)]
    else:
        logging.warning(
            f"MCP Server: Tool '{name}' không tồn tại hoặc không được cung cấp bởi server này."
        )
        error_payload = {
            "success": False,
            "message": f"Tool '{name}' không được hỗ trợ bởi server này.",
        }
        error_text = json.dumps(error_payload, ensure_ascii=False)
        return [mcp_types.TextContent(type="text", text=error_text)]

# --- MCP Server Runner ---
async def run_mcp_stdio_server():
    """Chạy MCP server, lắng nghe kết nối qua standard input/output."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logging.info("MCP Stdio Server: Bắt đầu handshake với client...")
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=app.name,
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
        logging.info("MCP Stdio Server: Kết thúc hoặc client đã ngắt kết nối.")

if __name__ == "__main__":
    logging.info("Khởi động School Management MCP Server qua stdio...")
    try:
        asyncio.run(run_mcp_stdio_server())
    except KeyboardInterrupt:
        logging.info("\nMCP Server (stdio) đã dừng bởi người dùng.")
    except Exception as e:
        logging.critical(
            f"MCP Server (stdio) gặp lỗi không xử lý được: {e}", exc_info=True
        )
    finally:
        logging.info("MCP Server (stdio) đã thoát.")