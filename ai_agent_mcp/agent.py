from pathlib import Path
import sys
import asyncio

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters, StdioConnectionParams

from school_prompt import SCHOOL_MANAGEMENT_PROMPT

# Tính đường dẫn tuyệt đối đến MCP server script
PATH_TO_SCHOOL_MCP_SERVER = str((Path(__file__).parent / "school_mcp_server.py").resolve())

# Khởi tạo agent quản lý trường học
school_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="school_management_agent",
    instruction=SCHOOL_MANAGEMENT_PROMPT,
    tools=[
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=sys.executable,  # Sử dụng Python từ môi trường hiện tại
                    args=[PATH_TO_SCHOOL_MCP_SERVER],
                ),
                timeout=30.0  # Timeout cao hơn cho API calls
            )
        )
    ],
)

async def main():
    """Chạy agent quản lý trường học."""
    print("🎓 Agent Quản lý Trường học đã sẵn sàng!")
    print("=" * 50)
    
    while True:
        try:
            user_input = input("\n👤 Bạn: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'thoát', 'bye']:
                print("👋 Tạm biệt! Chúc bạn một ngày tốt lành!")
                break
            
            if not user_input:
                continue
            
            print("\n🤖 Agent đang xử lý...")
            
            # Gửi yêu cầu đến agent
            response = await school_agent.arun(user_input)
            
            print(f"\n🎓 Assistant: {response}")
            
        except KeyboardInterrupt:
            print("\n👋 Tạm biệt!")
            break
        except Exception as e:
            print(f"\n❌ Lỗi: {str(e)}")
            print("Vui lòng thử lại.")

if __name__ == "__main__":
    asyncio.run(main())