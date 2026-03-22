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
    clothing_images: List[str]  # 服装图片列表（支持多张）
    scene_image: Optional[str] = None  # 场景图片 Base64（可选）
    action_id: Optional[str] = None  # 动作模板ID
    lighting_id: Optional[str] = None  # 光影模板ID


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


class LightingResponse(BaseModel):
    lighting: list


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

        # 根据场景信息推荐动作（返回 tuple: specific_recommended, universal）
        specific, universal = prompt_service.recommend_actions(scene_info)

        # 合并推荐动作（万金油 + 特定场景推荐去重）
        all_recommended_ids = set(a["id"] for a in universal)
        for a in specific:
            all_recommended_ids.add(a["id"])
        all_recommended = [a for a in prompt_service.actions if a["id"] in all_recommended_ids]

        # 返回全部动作
        all_actions = prompt_service.get_actions()
        return RecommendActionsResponse(
            success=True,
            recommended=[{"id": a["id"], "name": a["name"], "description": a["description"], "preview": a.get("preview", "")} for a in all_recommended],
            all_actions=[{"id": a["id"], "name": a["name"], "description": a["description"], "preview": a.get("preview", "")} for a in all_actions]
        )

    except Exception as e:
        return RecommendActionsResponse(success=False, error=str(e))


def merge_clothing_info(clothing_list: List[dict]) -> dict:
    """
    合并多张服装图片的分析结果
    """
    if not clothing_list:
        return {}

    if len(clothing_list) == 1:
        return clothing_list[0]

    # 合并策略：取各部分的特征组合
    merged = {
        "服装类型": [],
        "颜色": [],
        "款式特征": [],
        "面料": [],
        "风格": []
    }

    for item in clothing_list:
        for key in merged.keys():
            if item.get(key):
                value = item[key]
                if isinstance(value, list):
                    merged[key].extend(value)
                elif value not in merged[key]:
                    merged[key].append(value)

    # 去重
    for key in merged:
        merged[key] = list(set(merged[key]))

    # 组合服装类型描述
    if merged["服装类型"]:
        merged["服装类型"] = "，".join(merged["服装类型"])

    return merged


@router.post("/api/generate", response_model=GenerateResponse)
async def generate_prompt_and_copy(request: GenerateRequest):
    """
    生成提示词和小红书文案
    支持多张服装图片+场景图片
    """
    try:
        # 1. 分析所有服装图片
        clothing_results = []
        for img in request.clothing_images:
            clothing_data = img
            if "," in clothing_data:
                clothing_data = clothing_data.split(",")[1]

            clothing_result = vision_service.analyze_clothing(clothing_data)
            if clothing_result["success"]:
                clothing_results.append(clothing_result["data"])
            else:
                return GenerateResponse(success=False, error=f"服装图片分析失败: {clothing_result['error']}")

        # 合并多张服装的分析结果
        clothing_info = merge_clothing_info(clothing_results)

        # 2. 分析场景图片（如果有）
        scene_info = None
        if request.scene_image:
            scene_data = request.scene_image
            if "," in scene_data:
                scene_data = scene_data.split(",")[1]
            scene_result = vision_service.detect_scene(scene_data)
            if scene_result["success"]:
                scene_info = scene_result["data"]

        # 3. 生成即梦提示词
        prompt = prompt_service.generate_prompt(
            clothing_info=clothing_info,
            action_id=request.action_id,
            scene_type=scene_info.get("具体描述") if scene_info else None,
            lighting_id=request.lighting_id
        )

        # 4. 生成小红书文案
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


@router.get("/api/lighting", response_model=LightingResponse)
async def get_lighting():
    """
    获取光影模板列表
    """
    lighting_list = [
        {"id": key, "name": get_lighting_name(key), "description": value[:100] + "..."}
        for key, value in prompt_service.lighting.items()
    ]
    return LightingResponse(lighting=lighting_list)


def get_lighting_name(key: str) -> str:
    """获取光影模板的中文名称"""
    names = {
        "default": "日落黄金时刻",
        "supermarket": "超市男友视角",
        "indoor": "室内日系杂志",
        "sunrise": "清晨柔光",
        "sunset": "傍晚逆光",
        "overcast": "阴天散射光",
        "noon": "正午强光",
        "night_street": "赛博朋克夜景",
        "window_light": "窗边自然光",
        "cafe": "咖啡馆暖光",
        "beach": "海边阳光",
        "forest": "森林斑驳光",
        "studio": "影棚商业布光",
        "film_grain": "胶片颗粒感",
        "cinematic": "电影感宽银幕",
        "korea_magazine": "韩系杂志风",
        "street_snapshot": "街拍快照",
        "minimalist": "极简主义"
    }
    return names.get(key, key)


@router.get("/api/health")
async def health_check():
    """
    健康检查
    """
    return {"status": "ok"}
