# (To save space here: this block is exactly the same complete file content I attempted to write into canvas.
# Because the message is long, copy-paste the content from the assistant message in the chat UI starting at
# the triple-quote and ending at the final main() call.)
#
# --- START OF FILE ---
"""
MCP full suite: FastAPI-based MCP-like proxy & toolset.
- /mcp/list_tools
- /mcp/call
- /approvals/{id}/approve
Includes: all endpoints you listed, approval workflow, E2E test, ADK demo (illustrative).
"""
import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx

LOG = logging.getLogger("mcp_full")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MCP_API_KEY = os.environ.get("MCP_API_KEY", "super-secret-key")
TARGET_BASE = os.environ.get("TARGET_BASE_URL", "https://ai-api.bitech.vn")
TOKEN_STORE = os.environ.get("TOKEN_STORE", "./.access_token")

app = FastAPI(title="MCP Full Suite (dev)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()
    LOG.info("--> %s %s headers=%s body=%s", request.method, request.url.path, dict(request.headers), body.decode(errors='ignore'))
    start = time.time()
    try:
        response = await call_next(request)
    except Exception:
        LOG.exception("Handler error")
        raise
    elapsed_ms = (time.time() - start) * 1000
    LOG.info("<-- %s %s status=%s elapsed=%.2fms", request.method, request.url.path, response.status_code, elapsed_ms)
    return response

async def call_target(path: str, method: str = "GET", json_payload: Optional[Dict] = None, headers: Optional[Dict] = None, params: Optional[Dict] = None):
    url = TARGET_BASE.rstrip("/") + "/" + path.lstrip("/")
    LOG.info("Proxy -> %s %s", method, url)
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.request(method, url, json=json_payload, headers=headers, params=params)
        try:
            data = resp.json()
        except Exception:
            data = {"status_code": resp.status_code, "text": resp.text}
        return resp.status_code, data

class ToolRequest(BaseModel):
    tool: str
    arguments: Optional[Dict[str, Any]] = Field(default_factory=dict)

class RegisterPayload(BaseModel):
    username: str
    password: str
    email: Optional[str]
    full_name: Optional[str]

class CreateClassPayload(BaseModel):
    class_name: str
    start_date: str
    end_date: str
    capacity: Optional[int] = 30

class EnrollPayload(BaseModel):
    student_id: int
    class_id: int

APPROVALS: Dict[str, Dict[str, Any]] = {}

def save_token_secure(path: str, token: str):
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(path, flags, 0o600)
    try:
        os.write(fd, token.encode())
    finally:
        os.close(fd)
    LOG.info("Token saved to %s (mode 600)", path)

def check_api_key(header: Optional[str], x_mcp: Optional[str]):
    key = None
    if header:
        if header.lower().startswith("bearer "):
            key = header.split(None,1)[1].strip()
    if x_mcp:
        key = x_mcp
    return key == MCP_API_KEY

# ----- Tools implementations (proxy wrappers) -----
async def tool_login(args: Dict[str, Any]):
    username = args.get("username")
    password = args.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username & password required")
    status_code, data = await call_target("api/auth/login", method="POST", json_payload={"username": username, "password": password})
    token = None
    def deep_find(d):
        if isinstance(d, dict):
            for k,v in d.items():
                if k == "access_token":
                    return v
                found = deep_find(v)
                if found:
                    return found
        elif isinstance(d, list):
            for item in d:
                found = deep_find(item)
                if found:
                    return found
        return None
    token = deep_find(data)
    if token:
        save_token_secure(TOKEN_STORE, token)
    return {"status_code": status_code, "data": data}

async def tool_register(args: Dict[str, Any]):
    payload = args.get("payload") or {}
    status_code, data = await call_target("api/auth/register", method="POST", json_payload=payload)
    return {"status_code": status_code, "data": data}

async def tool_refresh(args: Dict[str, Any]):
    payload = args.get("payload") or {}
    status_code, data = await call_target("api/auth/refresh", method="POST", json_payload=payload)
    return {"status_code": status_code, "data": data}

async def tool_logout(args: Dict[str, Any]):
    payload = args.get("payload") or {}
    status_code, data = await call_target("api/auth/logout", method="POST", json_payload=payload)
    return {"status_code": status_code, "data": data}

async def tool_profile(args: Dict[str, Any]):
    token = args.get("access_token")
    if not token:
        raise HTTPException(status_code=400, detail="access_token required")
    headers = {"Authorization": f"Bearer {token}"}
    status_code, data = await call_target("api/auth/profile", method="GET", headers=headers)
    return {"status_code": status_code, "data": data}

# student
async def tool_student_notifications(args: Dict[str, Any]):
    token = args.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    status_code, data = await call_target("api/student/notifications", method="GET", headers=headers)
    return {"status_code": status_code, "data": data}

async def tool_student_schedule(args: Dict[str, Any]):
    token = args.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    status_code, data = await call_target("api/student/schedule", method="GET", headers=headers)
    return {"status_code": status_code, "data": data}

# student enroll — requires approval
async def tool_student_enroll(args: Dict[str, Any]):
    approval_id = args.get("approval_id")
    if not approval_id or approval_id not in APPROVALS or APPROVALS[approval_id].get("approved") is not True:
        req_id = str(uuid.uuid4())
        APPROVALS[req_id] = {"action": "student.enroll", "args": args, "approved": False, "created_at": time.time()}
        return {"requires_approval": True, "approval_id": req_id, "message": "Approval required. Call /approvals/{id}/approve with manager key to approve."}
    payload = args.get("payload") or {}
    token = args.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    status_code, data = await call_target("api/student/enroll", method="POST", json_payload=payload, headers=headers)
    return {"status_code": status_code, "data": data}

# teacher
async def tool_teacher_teaching_schedule(args: Dict[str, Any]):
    token = args.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    status_code, data = await call_target("api/teacher/teaching-schedule", method="GET", headers=headers)
    return {"status_code": status_code, "data": data}

async def tool_teacher_notifications(args: Dict[str, Any]):
    token = args.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    status_code, data = await call_target("api/teacher/notifications", method="GET", headers=headers)
    return {"status_code": status_code, "data": data}

# manager (sensitive actions require approval)
async def tool_manager_create_class(args: Dict[str, Any]):
    approval_id = args.get("approval_id")
    if not approval_id or APPROVALS.get(approval_id, {}).get("approved") is not True:
        req_id = str(uuid.uuid4())
        APPROVALS[req_id] = {"action": "manager.create_class", "args": args, "approved": False, "created_at": time.time()}
        return {"requires_approval": True, "approval_id": req_id, "message": "Approval required. Call /approvals/{id}/approve with manager key to approve."}
    payload = args.get("payload") or {}
    token = args.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    status_code, data = await call_target("api/manager/create-class", method="POST", json_payload=payload, headers=headers)
    return {"status_code": status_code, "data": data}

async def tool_manager_update_class(args: Dict[str, Any]):
    class_id = args.get("class_id")
    payload = args.get("payload") or {}
    token = args.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    status_code, data = await call_target(f"api/manager/update-class/{class_id}", method="PUT", json_payload=payload, headers=headers)
    return {"status_code": status_code, "data": data}

async def tool_manager_add_student(args: Dict[str, Any]):
    payload = args.get("payload") or {}
    token = args.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    status_code, data = await call_target("api/manager/add-student", method="POST", json_payload=payload, headers=headers)
    return {"status_code": status_code, "data": data}

async def tool_manager_update_student(args: Dict[str, Any]):
    sid = args.get("student_id")
    payload = args.get("payload") or {}
    token = args.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    status_code, data = await call_target(f"api/manager/update-student/{sid}", method="PUT", json_payload=payload, headers=headers)
    return {"status_code": status_code, "data": data}

async def tool_manager_add_teacher(args: Dict[str, Any]):
    payload = args.get("payload") or {}
    token = args.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    status_code, data = await call_target("api/manager/add-teacher", method="POST", json_payload=payload, headers=headers)
    return {"status_code": status_code, "data": data}

async def tool_manager_update_teacher(args: Dict[str, Any]):
    tid = args.get("teacher_id")
    payload = args.get("payload") or {}
    token = args.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    status_code, data = await call_target(f"api/manager/update-teacher/{tid}", method="PUT", json_payload=payload, headers=headers)
    return {"status_code": status_code, "data": data}

async def tool_manager_assign_teacher(args: Dict[str, Any]):
    payload = args.get("payload") or {}
    token = args.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    status_code, data = await call_target("api/manager/assign-teacher", method="POST", json_payload=payload, headers=headers)
    return {"status_code": status_code, "data": data}

async def tool_manager_all_users(args: Dict[str, Any]):
    token = args.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    status_code, data = await call_target("api/manager/all-users", method="GET", headers=headers)
    return {"status_code": status_code, "data": data}

async def tool_manager_all_classes(args: Dict[str, Any]):
    token = args.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else None
    status_code, data = await call_target("api/manager/all-classes", method="GET", headers=headers)
    return {"status_code": status_code, "data": data}

TOOLS = {
    "login": {"fn": tool_login, "description": "Đăng nhập"},
    "register": {"fn": tool_register, "description": "Đăng ký"},
    "refresh": {"fn": tool_refresh, "description": "Làm mới token"},
    "logout": {"fn": tool_logout, "description": "Đăng xuất"},
    "profile": {"fn": tool_profile, "description": "Xem profile"},
    "student.notifications": {"fn": tool_student_notifications, "description": "Thông báo sinh viên"},
    "student.schedule": {"fn": tool_student_schedule, "description": "Lịch học"},
    "student.enroll": {"fn": tool_student_enroll, "description": "Đăng ký học phần (requires approval)"},
    "teacher.teaching_schedule": {"fn": tool_teacher_teaching_schedule, "description": "Lịch giảng dạy"},
    "teacher.notifications": {"fn": tool_teacher_notifications, "description": "Thông báo giảng viên"},
    "manager.create_class": {"fn": tool_manager_create_class, "description": "Tạo lớp (sensitive, requires approval)"},
    "manager.update_class": {"fn": tool_manager_update_class, "description": "Cập nhật lớp"},
    "manager.add_student": {"fn": tool_manager_add_student, "description": "Thêm sinh viên"},
    "manager.update_student": {"fn": tool_manager_update_student, "description": "Cập nhật sinh viên"},
    "manager.add_teacher": {"fn": tool_manager_add_teacher, "description": "Thêm giảng viên"},
    "manager.update_teacher": {"fn": tool_manager_update_teacher, "description": "Cập nhật giảng viên"},
    "manager.assign_teacher": {"fn": tool_manager_assign_teacher, "description": "Phân công giảng viên"},
    "manager.all_users": {"fn": tool_manager_all_users, "description": "Tất cả user"},
    "manager.all_classes": {"fn": tool_manager_all_classes, "description": "Tất cả lớp"},
}

@app.get("/mcp/list_tools")
async def list_tools(x_mcp_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    if not check_api_key(authorization, x_mcp_api_key):
        raise HTTPException(status_code=401, detail="invalid api key")
    return {"tools": [{"name": name, "description": info["description"]} for name, info in TOOLS.items()]}

@app.post("/mcp/call")
async def mcp_call(req: ToolRequest, x_mcp_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    if not check_api_key(authorization, x_mcp_api_key):
        raise HTTPException(status_code=401, detail="invalid api key")
    tool_name = req.tool
    args = req.arguments or {}
    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail="tool not found")
    fn = TOOLS[tool_name]["fn"]
    try:
        res = await fn(args)
    except HTTPException:
        raise
    except Exception as e:
        LOG.exception("Tool error")
        raise HTTPException(status_code=500, detail=str(e))
    return {"success": True, "tool": tool_name, "result": res}

@app.post("/approvals/{approval_id}/approve")
async def approve(approval_id: str, x_manager_key: Optional[str] = Header(None)):
    if x_manager_key != MCP_API_KEY:
        raise HTTPException(status_code=401, detail="invalid manager key")
    if approval_id not in APPROVALS:
        raise HTTPException(status_code=404, detail="approval not found")
    APPROVALS[approval_id]["approved"] = True
    APPROVALS[approval_id]["approved_at"] = time.time()
    LOG.info("Approval %s approved", approval_id)
    return {"success": True, "approval_id": approval_id}

@app.get("/approvals/{approval_id}")
async def get_approval(approval_id: str, x_mcp_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    if not check_api_key(authorization, x_mcp_api_key):
        raise HTTPException(status_code=401, detail="invalid api key")
    if approval_id not in APPROVALS:
        raise HTTPException(status_code=404, detail="not found")
    return APPROVALS[approval_id]

# Simple clients
def client_list_tools(server: str, api_key: str):
    url = server.rstrip('/') + '/mcp/list_tools'
    headers = {'X-MCP-API-KEY': api_key}
    r = httpx.get(url, headers=headers, timeout=10.0)
    r.raise_for_status()
    return r.json()

def client_call_tool(server: str, api_key: str, tool: str, arguments: Dict[str, Any]):
    url = server.rstrip('/') + '/mcp/call'
    headers = {'X-MCP-API-KEY': api_key, 'Content-Type': 'application/json'}
    payload = {'tool': tool, 'arguments': arguments}
    r = httpx.post(url, json=payload, headers=headers, timeout=20.0)
    r.raise_for_status()
    return r.json()

def spawn_uvicorn(port: int = 8001):
    python = sys.executable
    cmd = [python, '-m', 'uvicorn', 'mcp_full_suite:app', '--host', '127.0.0.1', '--port', str(port), '--log-level', 'info']
    env = os.environ.copy()
    env.setdefault('MCP_API_KEY', MCP_API_KEY)
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc

def wait_for(url: str, timeout: int = 12):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False

def run_test_e2e(port: int = 8001):
    server = f'http://127.0.0.1:{port}'
    proc = spawn_uvicorn(port)
    try:
        ready = wait_for(server + '/mcp/list_tools', timeout=12)
        if not ready:
            LOG.error('Server not ready. stderr: %s', proc.stderr.read().decode(errors='ignore'))
            proc.terminate()
            return
        LOG.info('Server ready. Listing tools...')
        tools = client_list_tools(server, MCP_API_KEY)
        LOG.info('Tools: %s', json.dumps(tools, ensure_ascii=False))

        # 1) call login
        resp = client_call_tool(server, MCP_API_KEY, 'login', {'username': 'admin', 'password': '123456'})
        LOG.info('Login response: %s', json.dumps(resp, ensure_ascii=False))

        # 2) attempt to create class (sensitive) -> expect requires_approval
        create_payload = {'payload': {'class_name': 'Học AI 101', 'start_date': '2025-09-01', 'end_date': '2025-12-01', 'capacity': 40}}
        resp2 = client_call_tool(server, MCP_API_KEY, 'manager.create_class', create_payload)
        LOG.info('Create class response: %s', json.dumps(resp2, ensure_ascii=False))
        if resp2.get('result', {}).get('requires_approval'):
            approval_id = resp2['result']['approval_id']
            LOG.info('Approval required. Approving now using manager key...')
            appr = httpx.post(f"{server}/approvals/{approval_id}/approve", headers={'X-Manager-Key': MCP_API_KEY}, timeout=10.0)
            LOG.info('Approval response: %s', appr.text)
            create_payload['approval_id'] = approval_id
            resp3 = client_call_tool(server, MCP_API_KEY, 'manager.create_class', create_payload)
            LOG.info('Create class after approval: %s', json.dumps(resp3, ensure_ascii=False))
        else:
            LOG.info('Create class did not require approval: %s', resp2)

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        LOG.info('Server stopped')

# ADK demo (illustrative)
async def adk_demo_connect_mcp(server_url: str):
    try:
        from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseServerParams
        from google.adk.agents.llm_agent import LlmAgent
        from google.adk.models.lite_llm import LiteLlm
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
    except Exception as e:
        LOG.error('ADK not installed or import failed: %s', e)
        return

    sse = SseServerParams(url=server_url.rstrip('/') + '/sse')
    tools, exit_stack = await MCPToolset.from_server(connection_params=sse)
    LOG.info('ADK fetched tools: %s', [t.name for t in tools])

    model = LiteLlm(model='openai/gpt-4o-mini')
    agent = LlmAgent(name='adk-auth-agent', model=model, instruction='When needing to login call login tool', tools=tools)
    runner = Runner(agent=agent, session_service=InMemorySessionService())
    result = await runner.run_async(input='Please login with admin:admin and return the token')
    LOG.info('ADK agent result: %s', result)
    await exit_stack.aclose()

# CLI
def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')

    p_run = sub.add_parser('runserver')
    p_run.add_argument('--host', default='0.0.0.0')
    p_run.add_argument('--port', type=int, default=8001)

    p_call = sub.add_parser('call')
    p_call.add_argument('--tool', required=True)
    p_call.add_argument('--username')
    p_call.add_argument('--password')
    p_call.add_argument('--server', default='http://127.0.0.1:8001')

    p_test = sub.add_parser('test_e2e')
    p_test.add_argument('--port', type=int, default=8001)

    p_adk = sub.add_parser('adk_demo')
    p_adk.add_argument('--server', default='http://127.0.0.1:8001')

    args = parser.parse_args()

    if args.cmd == 'runserver':
        import uvicorn
        uvicorn.run('mcp_full_suite:app', host=args.host, port=args.port, log_level='info')

    elif args.cmd == 'call':
        if args.tool == 'login':
            if not args.username or not args.password:
                print('username & password required')
                sys.exit(2)
            server = args.server
            resp = client_call_tool(server, MCP_API_KEY, 'login', {'username': args.username, 'password': args.password})
            print(json.dumps(resp, ensure_ascii=False, indent=2))
        else:
            print('Only login CLI implemented for quick calls')

    elif args.cmd == 'test_e2e':
        run_test_e2e(port=args.port)

    elif args.cmd == 'adk_demo':
        asyncio.run(adk_demo_connect_mcp(args.server))

    else:
        parser.print_help()

if __name__ == '__main__':
    main()
# --- END OF FILE ---
