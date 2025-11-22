"""
User Profile Storage - 用户画像存储

管理用户兴趣标签和偏好设置。
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.config import DATA_DIR
from app.core.logger import logger


class UserProfileManager:
    """
    用户画像管理器。

    功能：
    - 存储和更新用户兴趣标签
    - 跟踪用户阅读历史
    - 管理用户偏好设置
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化用户画像管理器。

        Args:
            storage_path: 存储文件路径（默认使用 data/user_profiles.json）
        """
        self.storage_path = storage_path or os.path.join(DATA_DIR, "user_profiles.json")
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """确保存储文件存在。"""
        if not os.path.exists(self.storage_path):
            # 创建空的用户画像文件
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            logger.info(f"Created user profiles file: {self.storage_path}")

    def get_profile(self, user_id: str = "default") -> Dict[str, Any]:
        """
        获取用户画像。

        Args:
            user_id: 用户 ID（默认 "default"）

        Returns:
            用户画像数据
        """
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                profiles = json.load(f)

            if user_id not in profiles:
                # 创建默认画像
                default_profile = self._create_default_profile()
                profiles[user_id] = default_profile
                self._save_profiles(profiles)
                logger.info(f"Created default profile for user: {user_id}")
                return default_profile

            return profiles[user_id]

        except Exception as e:
            logger.error(f"Failed to get user profile for {user_id}: {e}")
            return self._create_default_profile()

    def update_interests(self, interests: List[str], user_id: str = "default") -> bool:
        """
        更新用户兴趣标签。

        Args:
            interests: 兴趣标签列表
            user_id: 用户 ID

        Returns:
            是否更新成功
        """
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                profiles = json.load(f)

            if user_id not in profiles:
                profiles[user_id] = self._create_default_profile()

            profiles[user_id]["interests"] = interests
            profiles[user_id]["updated_at"] = datetime.now().isoformat()

            self._save_profiles(profiles)
            logger.info(f"Updated interests for user {user_id}: {interests}")
            return True

        except Exception as e:
            logger.error(f"Failed to update interests for {user_id}: {e}")
            return False

    def add_interest(self, interest: str, user_id: str = "default") -> bool:
        """
        添加单个兴趣标签（如果不存在）。

        Args:
            interest: 兴趣标签
            user_id: 用户 ID

        Returns:
            是否添加成功
        """
        try:
            profile = self.get_profile(user_id)
            interests = profile.get("interests", [])

            if interest not in interests:
                interests.append(interest)
                return self.update_interests(interests, user_id)

            return True

        except Exception as e:
            logger.error(f"Failed to add interest '{interest}' for {user_id}: {e}")
            return False

    def remove_interest(self, interest: str, user_id: str = "default") -> bool:
        """
        移除兴趣标签。

        Args:
            interest: 要移除的兴趣标签
            user_id: 用户 ID

        Returns:
            是否移除成功
        """
        try:
            profile = self.get_profile(user_id)
            interests = profile.get("interests", [])

            if interest in interests:
                interests.remove(interest)
                return self.update_interests(interests, user_id)

            return True

        except Exception as e:
            logger.error(f"Failed to remove interest '{interest}' for {user_id}: {e}")
            return False

    def add_to_history(self, item_id: str, title: str, topic: str, user_id: str = "default") -> bool:
        """
        添加文章到阅读历史。

        Args:
            item_id: 文章 ID
            title: 文章标题
            topic: 文章话题
            user_id: 用户 ID

        Returns:
            是否添加成功
        """
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                profiles = json.load(f)

            if user_id not in profiles:
                profiles[user_id] = self._create_default_profile()

            # 添加到历史记录
            history_entry = {
                "item_id": item_id,
                "title": title,
                "topic": topic,
                "read_at": datetime.now().isoformat()
            }

            profiles[user_id]["reading_history"].insert(0, history_entry)

            # 限制历史记录长度
            max_history = 100
            profiles[user_id]["reading_history"] = profiles[user_id]["reading_history"][:max_history]

            # 自动更新兴趣标签（基于阅读历史）
            self._auto_update_interests(profiles[user_id])

            self._save_profiles(profiles)
            logger.info(f"Added article {item_id} to history for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add to history for {user_id}: {e}")
            return False

    def get_reading_history(self, user_id: str = "default", limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取阅读历史。

        Args:
            user_id: 用户 ID
            limit: 返回记录数量

        Returns:
            阅读历史列表
        """
        try:
            profile = self.get_profile(user_id)
            history = profile.get("reading_history", [])
            return history[:limit]

        except Exception as e:
            logger.error(f"Failed to get reading history for {user_id}: {e}")
            return []

    def update_preference(self, key: str, value: Any, user_id: str = "default") -> bool:
        """
        更新用户偏好设置。

        Args:
            key: 设置键
            value: 设置值
            user_id: 用户 ID

        Returns:
            是否更新成功
        """
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                profiles = json.load(f)

            if user_id not in profiles:
                profiles[user_id] = self._create_default_profile()

            profiles[user_id]["preferences"][key] = value
            profiles[user_id]["updated_at"] = datetime.now().isoformat()

            self._save_profiles(profiles)
            logger.info(f"Updated preference '{key}' for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update preference for {user_id}: {e}")
            return False

    def get_all_users(self) -> List[str]:
        """
        获取所有用户 ID。

        Returns:
            用户 ID 列表
        """
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                profiles = json.load(f)
            return list(profiles.keys())

        except Exception as e:
            logger.error(f"Failed to get user list: {e}")
            return []

    def _create_default_profile(self) -> Dict[str, Any]:
        """创建默认用户画像。"""
        return {
            "interests": [],
            "reading_history": [],
            "preferences": {
                "min_score": 0,
                "time_range_days": 3,
                "recommendations_count": 5
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

    def _save_profiles(self, profiles: Dict[str, Any]):
        """保存用户画像到文件。"""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(profiles, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save profiles: {e}")
            raise

    def _auto_update_interests(self, profile: Dict[str, Any]):
        """
        基于阅读历史自动更新兴趣标签。

        规则：
        - 统计最近 20 篇阅读的文章话题
        - 如果某个话题出现 3 次以上，且不在兴趣列表中，自动添加
        """
        try:
            history = profile.get("reading_history", [])[:20]
            interests = profile.get("interests", [])

            # 统计话题频次
            topic_count = {}
            for entry in history:
                topic = entry.get("topic")
                if topic:
                    topic_count[topic] = topic_count.get(topic, 0) + 1

            # 添加高频话题
            for topic, count in topic_count.items():
                if count >= 3 and topic not in interests:
                    interests.append(topic)
                    logger.info(f"Auto-added interest: {topic} (appeared {count} times)")

            profile["interests"] = interests

        except Exception as e:
            logger.warning(f"Failed to auto-update interests: {e}")
