"""
API 路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from services.vision import VisionService
from services.prompt import PromptService
from services.copy import CopyService

router = APIRouter()

# 初始化服务
vision_service = VisionService()
prompt_service = PromptService()
copy_service = CopyService()


# ============ 请求/响应模型 ============

class GenerateRequest(BaseModel):
    clothing_image: str  # 服装图片 Base64
    scene_image: Optional[str] = None  # 场景图片 Base64（可选）
    action_id: Optional[str] = None  # 动作模板ID


class RecommendActionsRequest(BaseModel):
    scene_image: str  # 场景图片 Base64


class RecommendActionsResponse(BaseModel):
    success: bool
    recommended: Optional[List[dict]] = None
    all_actions: Optional[List[dict]] = None
    error: Optional[str] = None


class GenerateResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class ActionsResponse(BaseModel):
    actions: list


# ============ API 路由 ============

@router.post("/api/recommend-actions", response_model=RecommendActionsResponse)
async def recommend_actions(request: RecommendActionsRequest):
    """
    根据场景图片分析并推荐匹配的动作
    """
    try:
        # 解析场景图片
        scene_data = request.scene_image
        if "," in scene_data:
            scene_data = scene_data.split(",")[1]

        # 使用LLM分析场景
        scene_result = vision_service.detect_scene(scene_data)
        if not scene_result["success"]:
            return RecommendActionsResponse(
                success=False,
                error=f"场景分析失败: {scene_result['error']}"
            )

        scene_info = scene_result["data"]

        # 根据场景信息推荐动作
        recommended = prompt_service.recommend_actions(scene_info)

        # 返回推荐动作和全部动作
        all_actions = prompt_service.get_actions()
        return RecommendActionsResponse(
            success=True,
            recommended=[{"id": a["id"], "name": a["name"], "description": a["description"], "preview": a.get("preview", "")} for a in recommended],
            all_actions=[{"id": a["id"], "name": a["name"], "description": a["description"], "preview": a.get("preview", "")} for a in all_actions]
        )

    except Exception as e:
        return RecommendActionsResponse(success=False, error=str(e))


@router.post("/api/generate", response_model=GenerateResponse)
async def generate_prompt_and_copy(request: GenerateRequest):
    """
    生成提示词和小红书文案
    支持服装图片+场景图片
    """
    try:
        # 1. 解析服装图片（去掉前缀）
        clothing_data = request.clothing_image
        if "," in clothing_data:
            clothing_data = clothing_data.split(",")[1]

        # 2. 使用LLM分析服装图片
        clothing_result = vision_service.analyze_clothing(clothing_data)
        if not clothing_result["success"]:
            return GenerateResponse(success=False, error=f"服装图片分析失败: {clothing_result['error']}")

        clothing_info = clothing_result["data"]

        # 3. 分析场景图片（如果有）
        scene_info = None
        if request.scene_image:
            scene_data = request.scene_image
            if "," in scene_data:
                scene_data = scene_data.split(",")[1]
            scene_result = vision_service.detect_scene(scene_data)
            if scene_result["success"]:
                scene_info = scene_result["data"]

        # 4. 生成即梦提示词
        prompt = prompt_service.generate_prompt(
            clothing_info=clothing_info,
            action_id=request.action_id,
            scene_type=scene_info.get("具体描述") if scene_info else None
        )

        # 5. 生成小红书文案
        copy_result = copy_service.generate_xiaohongshu(
            clothing_info=clothing_info,
            scene_info=scene_info
        )

        return GenerateResponse(
            success=True,
            data={
                "prompt": prompt,
                "xiaohongshu": copy_result["data"]
            }
        )

    except Exception as e:
        return GenerateResponse(success=False, error=str(e))


@router.get("/api/actions", response_model=ActionsResponse)
async def get_actions():
    """
    获取动作模板列表
    """
    return ActionsResponse(actions=prompt_service.get_actions())


@router.get("/api/scenes")
async def get_scenes():
    """
    获取场景模板列表
    """
    return prompt_service.get_scenes()


@router.get("/api/health")
async def health_check():
    """
    健康检查
    """
    return {"status": "ok"}
