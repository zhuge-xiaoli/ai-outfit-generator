"""
提示词生成服务
根据服装分析和动作模板生成即梦提示词
"""
import json
import os
import random


class PromptService:
    def __init__(self):
        # 加载动作模板
        template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "actions.json")
        with open(template_path, "r", encoding="utf-8") as f:
            self.templates = json.load(f)

        self.actions = self.templates["actions"]
        self.lighting = self.templates["lighting_templates"]
        self.scenes = self.templates["scenes"]

        # 场景元素 → 推荐动作ID映射（仅限有明显道具的场景）
        self.scene_to_actions = {
            # 台阶/楼梯/沙发相关
            "台阶": ["12", "9"],
            "楼梯": ["12", "9"],
            "沙发": ["12", "9"],
            "凳子": ["12", "9"],
            # 墙面/门框相关
            "墙面": ["10", "2"],
            "门框": ["10", "2"],
            # 桌子/咖啡桌相关
            "桌子": ["7", "6"],
            "咖啡桌": ["7", "6"],
            # 街道/道路相关
            "街道": ["3", "8"],
            "道路": ["3", "8"],
        }

        # 万金油动作 - 适合任何场景
        self.universal_action_ids = ["4", "5", "6"]

    def recommend_actions(self, scene_info: dict) -> tuple:
        """
        根据场景信息推荐匹配的动作
        返回 (specific_recommended, universal)
        specific_recommended: 基于特定场景元素推荐的动作
        universal: 万金油动作（始终返回）
        """
        universal = [a for a in self.actions if a["id"] in self.universal_action_ids]

        if not scene_info:
            return [], universal

        scene_elements = scene_info.get("场景元素", [])
        if isinstance(scene_elements, str):
            try:
                import ast
                scene_elements = ast.literal_eval(scene_elements)
            except:
                scene_elements = []

        if not scene_elements:
            return [], universal

        recommended_ids = set()
        for element in scene_elements:
            element_lower = element.lower() if isinstance(element, str) else str(element)
            for key, action_ids in self.scene_to_actions.items():
                if key.lower() in element_lower or element_lower in key.lower():
                    recommended_ids.update(action_ids)

        if not recommended_ids:
            return [], universal

        specific = [a for a in self.actions if a["id"] in recommended_ids]
        return specific, universal

    def generate_prompt(self, clothing_info: dict, action_id: str = None, scene_type: str = None, lighting_id: str = None) -> str:
        """
        生成即梦提示词
        """
        # 如果没有指定动作，随机选择一个
        if not action_id:
            action = random.choice(self.actions)
        else:
            action = next((a for a in self.actions if a["id"] == action_id), self.actions[0])

        # 获取动作模板
        action_template = action["template"]

        # 根据用户选择的光影ID或场景类型选择光线模板
        if lighting_id and lighting_id in self.lighting:
            lighting_template = self.lighting[lighting_id]
        elif scene_type and "超市" in scene_type:
            lighting_template = self.lighting["supermarket"]
        elif scene_type and "室内" in scene_type:
            lighting_template = self.lighting["indoor"]
        else:
            lighting_template = self.lighting["default"]

        # 服装描述
        clothing_desc = self._build_clothing_description(clothing_info)

        # 场景描述
        scene_desc = self._build_scene_description(scene_type)

        # 组合提示词
        prompt = f"""图1的这位21岁东亚男大学生日系穿搭博主。
{action_template}
他身穿{clothing_desc}。
背景是{scene_desc}。
{lighting_template}"""

        return prompt

    def _build_clothing_description(self, clothing_info: dict) -> str:
        """构建服装描述"""
        parts = []

        if clothing_info.get("颜色"):
            parts.append(clothing_info["颜色"])

        if clothing_info.get("款式特征"):
            parts.append(clothing_info["款式特征"])

        if clothing_info.get("服装类型"):
            parts.append(clothing_info["服装类型"])

        return "，".join(parts) if parts else "时尚休闲穿搭"

    def _build_scene_description(self, scene_type: str = None) -> str:
        """构建场景描述"""
        if scene_type:
            return scene_type
        return "浅灰色背景，突出了服装的主体。整体的光线柔和均匀，没有强烈的阴影，营造出舒适的氛围。"

    def get_actions(self) -> list:
        """获取所有动作模板"""
        return [{"id": a["id"], "name": a["name"], "description": a["description"], "preview": a.get("preview", "")} for a in self.actions]

    def get_scenes(self) -> dict:
        """获取所有场景模板"""
        return self.scenes
