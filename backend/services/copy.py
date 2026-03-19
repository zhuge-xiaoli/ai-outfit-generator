"""
文案生成服务
生成小红书风格的标题和正文
"""
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()


class CopyService:
    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.base_url = "https://dashscope.aliyuncs.com/api/v1"
        self.model = "qwen-turbo"

    def generate_xiaohongshu(self, clothing_info: dict, scene_info: dict = None) -> dict:
        """
        生成小红书风格的文案
        """
        # 构建上下文
        clothing_desc = self._format_clothing_info(clothing_info)
        scene_desc = self._format_scene_info(scene_info) if scene_info else "日常穿搭"

        prompt = f"""你是一位小红书穿搭博主，请为以下穿搭生成一篇爆款文案：

穿搭信息：{clothing_desc}
场景：{scene_desc}

请按以下JSON格式输出：
{{
    "title": "生成的标题（20字以内，带emoji，有悬念或情绪词）",
    "content": "生成的正文（100-200字，第一人称叙事，带emoji，有互动引导）",
    "tags": ["#标签1", "#标签2", "#标签3", "#标签4"]
}}

要求：
- 标题要吸引眼球，有带入感
- 正文要自然口语化，像真人分享
- 至少3个相关标签
- 带上具体的服装品牌或搭配建议
- 只输出JSON，不要其他内容"""

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.base_url}/services/aigc/text-generation/generation",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "X-DashScope-Async": "disable"
                    },
                    json={
                        "model": self.model,
                        "input": {
                            "prompt": prompt
                        },
                        "parameters": {
                            "max_tokens": 1500,
                            "result_format": "message"
                        }
                    }
                )

                if response.status_code != 200:
                    return {"success": True, "data": self._default_copy(clothing_desc)}

                result = response.json()
                content = result["output"]["choices"][0]["message"]["content"]

                # 尝试解析JSON
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    import re
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    if match:
                        data = json.loads(match.group())
                    else:
                        data = self._default_copy(clothing_desc)

                return {"success": True, "data": data}

        except Exception as e:
            # 返回默认文案
            return {"success": True, "data": self._default_copy(clothing_desc)}

    def _format_clothing_info(self, clothing_info: dict) -> str:
        """格式化服装信息"""
        parts = []
        if clothing_info.get("颜色"):
            parts.append(f"颜色：{clothing_info['颜色']}")
        if clothing_info.get("服装类型"):
            parts.append(f"类型：{clothing_info['服装类型']}")
        if clothing_info.get("款式特征"):
            parts.append(f"款式：{clothing_info['款式特征']}")
        if clothing_info.get("适用场景"):
            parts.append(f"场景：{clothing_info['适用场景']}")

        return "，".join(parts) if parts else "时尚穿搭"

    def _format_scene_info(self, scene_info: dict) -> str:
        """格式化场景信息"""
        if scene_info and scene_info.get("具体描述"):
            return scene_info["具体描述"]
        return "日常穿搭"

    def _default_copy(self, clothing_desc: str) -> dict:
        """生成默认文案"""
        return {
            "title": "这套穿搭也太绝了吧！🧥",
            "content": f"家人们！今天这套{clothing_desc}真的绝了！\n\n简单搭配就很有氛围感，男朋友穿起来也太帅了吧！🤩\n\n姐妹们觉得怎么样？评论区告诉我！👇",
            "tags": ["#男友穿搭", "#男生穿搭", "#OOTD", "#氛围感"]
        }
