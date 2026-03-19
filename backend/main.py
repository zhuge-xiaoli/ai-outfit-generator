"""
AI穿搭提示词生成工具 - 后端服务
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from api.routes import router

# 创建FastAPI应用
app = FastAPI(
    title="AI穿搭提示词生成器",
    description="上传图片，自动生成即梦提示词和小红书文案",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)

# 获取前端目录路径
frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

@app.get("/")
async def root():
    """返回前端页面"""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "AI穿搭提示词生成器 API", "docs": "/docs"}


# 挂载静态文件
static_path = os.path.join(frontend_path, "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# 挂载动作示范图
action_previews_path = os.path.join(frontend_path, "action-previews")
print(f"[DEBUG] Action previews path: {action_previews_path}")
print(f"[DEBUG] Action previews exists: {os.path.exists(action_previews_path)}")
if os.path.exists(action_previews_path):
    print(f"[DEBUG] Files: {os.listdir(action_previews_path)}")
    app.mount("/action-previews", StaticFiles(directory=action_previews_path, html=False), name="action-previews")
    print("[DEBUG] /action-previews mounted successfully")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
