"""
LLM 视觉分析服务
使用 通义千问 API 分析图片中的服装特征
"""
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()


class VisionService:
    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.base_url = "https://dashscope.aliyuncs.com/api/v1"
        self.model = "qwen-vl-plus"

    def analyze_clothing(self, image_base64: str) -> dict:
        """
        分析图片中的服装特征
        """
        prompt = """请分析这张图片中的服装信息，请用以下JSON格式输出：
{
    "服装类型": "外套/上衣/裤子/裙子/鞋子等",
    "颜色": "具体颜色描述",
    "款式特征": "宽松/修身/细节设计等",
    "面料质感": "看起来像什么材质",
    "适用场景": "适合什么场景穿着",
    "搭配建议": "可以搭配什么类型的衣服"
}
只输出JSON，不要其他内容。"""

        try:
            # 通义千问 API 调用
            with httpx.Client(timeout=180.0) as client:
                response = client.post(
                    f"{self.base_url}/services/aigc/multimodal-generation/generation",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "X-DashScope-Async": "disable"
                    },
                    json={
                        "model": self.model,
                        "input": {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "image": f"data:image/jpeg;base64,{image_base64}"
                                        },
                                        {
                                            "text": prompt
                                        }
                                    ]
                                }
                            ]
                        },
                        "parameters": {
                            "max_tokens": 1000,
                            "result_format": "message"
                        }
                    }
                )

                if response.status_code != 200:
                    return {"success": False, "error": f"API错误: {response.text}"}

                result = response.json()
                content = result["output"]["choices"][0]["message"]["content"][0]["text"]

                # 尝试解析JSON
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    import re
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    if match:
                        data = json.loads(match.group())
                    else:
                        data = {
                            "服装类型": "未知",
                            "颜色": "未知",
                            "款式特征": "未知",
                            "面料质感": "未知",
                            "适用场景": "未知",
                            "搭配建议": "未知"
                        }

                return {"success": True, "data": data}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def detect_scene(self, image_base64: str) -> dict:
        """
        识别图片中的场景（忽略人物，只分析环境）
        """
        prompt = """请分析这张图片的场景环境，请注意：
1. 忽略图片中的任何人物，只描述环境背景
2. 如果有人物，请描述人物周围的场景元素

请用以下JSON格式输出：
{
    "场景类型": "室内/室外/超市/街道/咖啡厅/办公室/家居等",
    "具体描述": "场景的具体特征，包括墙面、地面、物品、装饰等",
    "光线": "自然光/人工光/混合光，描述光线特点",
    "背景元素": "有哪些明显的背景物体（不要包含人物）",
    "色调": "整体色调，如暖色调、冷色调、黑白等",
    "场景元素": ["列出图中存在的场景元素，如：椅子、台阶、墙面、路灯、柱子、桌子、栏杆、门框、窗户、楼梯、货架、展示台、咖啡桌、书架等"]
}
只输出JSON，不要其他内容。"""

        try:
            with httpx.Client(timeout=180.0) as client:
                response = client.post(
                    f"{self.base_url}/services/aigc/multimodal-generation/generation",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "X-DashScope-Async": "disable"
                    },
                    json={
                        "model": self.model,
                        "input": {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "image": f"data:image/jpeg;base64,{image_base64}"
                                        },
                                        {
                                            "text": prompt
                                        }
                                    ]
                                }
                            ]
                        },
                        "parameters": {
                            "max_tokens": 1000,
                            "result_format": "message"
                        }
                    }
                )

                if response.status_code != 200:
                    return {"success": False, "error": f"API错误: {response.text}"}

                result = response.json()
                content = result["output"]["choices"][0]["message"]["content"][0]["text"]

                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    import re
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    if match:
                        data = json.loads(match.group())
                    else:
                        data = {
                            "场景类型": "未知",
                            "具体描述": "未知",
                            "光线": "未知",
                            "背景元素": "未知",
                            "场景元素": []
                        }

                return {"success": True, "data": data}

        except Exception as e:
            return {"success": False, "error": str(e)}
