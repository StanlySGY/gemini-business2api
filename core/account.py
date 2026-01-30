"""账户管理模块

负责账户配置、多账户协调和会话缓存管理
"""
import asyncio
import json
import logging
import os
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, TYPE_CHECKING, Iterable

from fastapi import HTTPException

# 导入存储层（支持数据库）
from core import storage

if TYPE_CHECKING:
    from core.jwt import JWTManager

logger = logging.getLogger(__name__)

# HTTP错误名称映射
HTTP_ERROR_NAMES = {
    400: "参数错误",
    401: "认证错误",
    403: "权限错误",
    429: "限流",
    502: "网关错误",
    503: "服务不可用"
}

# 配额类型定义
QUOTA_TYPES = {
    "text": "对话",
    "images": "绘图",
    "videos": "视频"
}

@dataclass
class AccountConfig:
    """单个账户配置"""
    account_id: str
    secure_c_ses: str
    host_c_oses: Optional[str]
    csesidx: str
    config_id: str
    expires_at: Optional[str] = None  # 账户过期时间 (格式: "2025-12-23 10:59:21")
    disabled: bool = False  # 手动禁用状态
    mail_provider: Optional[str] = None
    mail_address: Optional[str] = None
    mail_password: Optional[str] = None
    mail_client_id: Optional[str] = None
    mail_refresh_token: Optional[str] = None
    mail_tenant: Optional[str] = None
    # 邮箱自定义配置字段（用于账户级别的邮箱服务配置）
    mail_base_url: Optional[str] = None
    mail_jwt_token: Optional[str] = None
    mail_verify_ssl: Optional[bool] = None
    mail_domain: Optional[str] = None
    mail_api_key: Optional[str] = None

    def get_remaining_hours(self) -> Optional[float]:
        """计算账户剩余小时数"""
        if not self.expires_at:
            return None
        try:
            # 解析过期时间（假设为北京时间）
            beijing_tz = timezone(timedelta(hours=8))
            expire_time = datetime.strptime(self.expires_at, "%Y-%m-%d %H:%M:%S")
            expire_time = expire_time.replace(tzinfo=beijing_tz)

            # 当前时间（北京时间）
            now = datetime.now(beijing_tz)

            # 计算剩余时间
            remaining = (expire_time - now).total_seconds() / 3600
            return remaining
        except Exception:
            return None

    def is_expired(self) -> bool:
        """检查账户是否已过期"""
        remaining = self.get_remaining_hours()
        if remaining is None:
            return False  # 未设置过期时间，默认不过期
        return remaining <= 0


@dataclass(frozen=True)
class CooldownConfig:
    text: int
    images: int
    videos: int
    global_cooldown: int


@dataclass(frozen=True)
class RetryPolicy:
    cooldowns: CooldownConfig


def format_account_expiration(remaining_hours: Optional[float]) -> tuple:
    """
    格式化账户过期时间显示（基于12小时过期周期）

    Args:
        remaining_hours: 剩余小时数（None表示未设置过期时间）

    Returns:
        (status, status_color, expire_display) 元组
    """
    if remaining_hours is None:
        # 未设置过期时间时显示为"未设置"
        return ("未设置", "#9e9e9e", "未设置")
    elif remaining_hours <= 0:
        return ("已过期", "#f44336", "已过期")
    elif remaining_hours < 3:  # 少于3小时
        return ("即将过期", "#ff9800", f"{remaining_hours:.1f} 小时")
    else:  # 3小时及以上，统一显示小时
        return ("正常", "#4caf50", f"{remaining_hours:.1f} 小时")


class AccountManager:
    """单个账户管理器"""
    def __init__(
        self,
        config: AccountConfig,
        http_client,
        user_agent: str,
        retry_policy: RetryPolicy,
    ):
        self.config = config
        self.http_client = http_client
        self.user_agent = user_agent
        # 冷却时间配置
        self.rate_limit_cooldown_seconds = retry_policy.cooldowns.text  # 向后兼容
        self.text_rate_limit_cooldown_seconds = retry_policy.cooldowns.text
        self.images_rate_limit_cooldown_seconds = retry_policy.cooldowns.images
        self.videos_rate_limit_cooldown_seconds = retry_policy.cooldowns.videos
        self.global_cooldown_seconds = retry_policy.cooldowns.global_cooldown  # 新增：全局冷却
        self.jwt_manager: Optional['JWTManager'] = None  # 延迟初始化
        self.is_available = True
        self.last_error_time = 0.0  # 保留用于统计
        self.last_cooldown_time = 0.0  # 全局冷却时间戳
        self.quota_cooldowns: Dict[str, float] = {}  # 按配额类型的冷却时间戳
        self.conversation_count = 0  # 累计成功次数（用于统计展示）
        self.failure_count = 0  # 累计失败次数（用于统计展示）
        self.session_usage_count = 0  # 本次启动后使用次数（用于均衡轮询）

    def handle_non_http_error(self, error_context: str = "", request_id: str = "") -> None:
        """
        统一处理非HTTP错误（网络错误、解析错误等）- 极简版：只有冷却

        Args:
            error_context: 错误上下文（如"JWT获取"、"聊天请求"）
            request_id: 请求ID（用于日志）
        """
        req_tag = f"[req_{request_id}] " if request_id else ""
        self.last_error_time = time.time()
        self.last_cooldown_time = time.time()
        self.is_available = False
        logger.warning(
            f"[ACCOUNT] [{self.config.account_id}] {req_tag}"
            f"{error_context}失败，账户将休息{self.global_cooldown_seconds}秒后自动恢复"
        )

    def _get_quota_cooldown_seconds(self, quota_type: Optional[str]) -> int:
        if quota_type == "images":
            return self.images_rate_limit_cooldown_seconds
        if quota_type == "videos":
            return self.videos_rate_limit_cooldown_seconds
        return self.text_rate_limit_cooldown_seconds

    def apply_retry_policy(self, retry_policy: RetryPolicy) -> None:
        """Apply updated retry policy to this account manager."""
        self.rate_limit_cooldown_seconds = retry_policy.cooldowns.text  # 向后兼容
        self.text_rate_limit_cooldown_seconds = retry_policy.cooldowns.text
        self.images_rate_limit_cooldown_seconds = retry_policy.cooldowns.images
        self.videos_rate_limit_cooldown_seconds = retry_policy.cooldowns.videos
        self.global_cooldown_seconds = retry_policy.cooldowns.global_cooldown  # 新增

    def handle_http_error(self, status_code: int, error_detail: str = "", request_id: str = "", quota_type: Optional[str] = None) -> None:
        """
        统一处理HTTP错误 - 极简版：只有冷却，没有永久禁用

        Args:
            status_code: HTTP状态码
            error_detail: 错误详情
            request_id: 请求ID（用于日志）
            quota_type: 配额类型（"text", "images", "videos"），用于429错误按类型冷却

        处理逻辑：
            - 400: 参数错误，不计入失败（客户端问题）
            - 429 + quota_type: 按配额类型冷却（对话/绘图/视频独立冷却）
            - 429 无quota_type: 全局冷却
            - 401/403: 全局冷却
            - 502/503及其他HTTP错误: 全局冷却（新增）
        """
        req_tag = f"[req_{request_id}] " if request_id else ""

        # 400参数错误：不计入失败（客户端问题）
        if status_code == 400:
            logger.warning(
                f"[ACCOUNT] [{self.config.account_id}] {req_tag}"
                f"HTTP 400参数错误（不计入失败）{': ' + error_detail[:100] if error_detail else ''}"
            )
            return

        # 429限流错误：按配额类型冷却或全局冷却
        if status_code == 429:
            if quota_type and quota_type in QUOTA_TYPES:
                # 按配额类型冷却（不影响账户整体可用性）
                self.quota_cooldowns[quota_type] = time.time()
                cooldown_seconds = self._get_quota_cooldown_seconds(quota_type)
                logger.warning(
                    f"[ACCOUNT] [{self.config.account_id}] {req_tag}"
                    f"{QUOTA_TYPES[quota_type]}配额限流，将在{cooldown_seconds}秒后自动恢复"
                    f"{': ' + error_detail[:100] if error_detail else ''}"
                )
            else:
                # 全局冷却（未指定配额类型）
                self.last_cooldown_time = time.time()
                self.is_available = False
                logger.warning(
                    f"[ACCOUNT] [{self.config.account_id}] {req_tag}"
                    f"遇到429限流，账户将休息{self.global_cooldown_seconds}秒后自动恢复"
                    f"{': ' + error_detail[:100] if error_detail else ''}"
                )
            return

        # 401/403/502/503及其他HTTP错误：全局冷却（统一处理）
        self.last_error_time = time.time()
        self.last_cooldown_time = time.time()
        self.is_available = False
        error_type = HTTP_ERROR_NAMES.get(status_code, f"HTTP {status_code}")
        logger.warning(
            f"[ACCOUNT] [{self.config.account_id}] {req_tag}"
            f"遇到{error_type}错误，账户将休息{self.global_cooldown_seconds}秒后自动恢复"
            f"{': ' + error_detail[:100] if error_detail else ''}"
        )

    def is_quota_available(self, quota_type: str) -> bool:
        """检查指定配额是否可用（冷却中则不可用）。"""
        if quota_type not in QUOTA_TYPES:
            return True

        cooldown_time = self.quota_cooldowns.get(quota_type)
        if not cooldown_time:
            return True

        elapsed = time.time() - cooldown_time
        cooldown_seconds = self._get_quota_cooldown_seconds(quota_type)
        if elapsed < cooldown_seconds:
            return False

        # 冷却已过期，清理
        del self.quota_cooldowns[quota_type]
        return True

    def are_quotas_available(self, quota_types: Optional[Iterable[str]] = None) -> bool:
        """
        检查多个配额类型是否都可用。

        注意：如果对话配额受限，所有配额都不可用（对话是基础功能）
        """
        if not quota_types:
            return True
        if isinstance(quota_types, str):
            quota_types = [quota_types]

        # 如果对话配额受限，所有配额都不可用
        if not self.is_quota_available("text"):
            return False

        # 检查其他配额
        return all(self.is_quota_available(qt) for qt in quota_types if qt != "text")

    async def get_jwt(self, request_id: str = "") -> str:
        """获取 JWT token (带错误处理)"""
        # 检查账户是否过期
        if self.config.is_expired():
            self.is_available = False
            logger.warning(f"[ACCOUNT] [{self.config.account_id}] 账户已过期，已自动禁用")
            raise HTTPException(403, f"Account {self.config.account_id} has expired")

        try:
            if self.jwt_manager is None:
                # 延迟初始化 JWTManager (避免循环依赖)
                from core.jwt import JWTManager
                self.jwt_manager = JWTManager(self.config, self.http_client, self.user_agent)
            jwt = await self.jwt_manager.get(request_id)
            self.is_available = True
            return jwt
        except Exception as e:
            # 使用统一的错误处理入口
            if isinstance(e, HTTPException):
                self.handle_http_error(e.status_code, str(e.detail) if hasattr(e, 'detail') else "", request_id)
            else:
                self.handle_non_http_error("JWT获取", request_id)
            raise

    def should_retry(self) -> bool:
        """检查账户是否可重试 - 极简版：只检查冷却期"""
        if self.is_available:
            return True

        current_time = time.time()

        # 检查冷却期（所有错误冷却期后自动恢复）
        if self.last_cooldown_time > 0:
            if current_time - self.last_cooldown_time > self.global_cooldown_seconds:
                # 冷却期已过，自动恢复账户可用性
                self.is_available = True
                self.last_cooldown_time = 0.0
                logger.info(f"[ACCOUNT] [{self.config.account_id}] 冷却期已过，账户已自动恢复")
                return True
            return False  # 仍在冷却期

        # 如果没有冷却时间戳但账户不可用，可能是手动禁用
        return False

    def get_cooldown_info(self) -> tuple[int, str | None]:
        """获取账户冷却信息"""
        current_time = time.time()

        # 检查冷却期
        if self.last_cooldown_time > 0:
            remaining = self.global_cooldown_seconds - (current_time - self.last_cooldown_time)
            if remaining > 0:
                return (int(remaining), "全局冷却")

        # 如果账户可用且没有冷却，返回正常状态
        if self.is_available:
            return (0, None)

        # 账户不可用但没有冷却时间戳（可能是手动禁用）
        return (-1, "手动禁用")

    def get_quota_status(self) -> Dict[str, any]:
        """
        获取配额状态（被动检测模式）

        Returns:
            {
                "quotas": {
                    "text": {"available": bool, "remaining_seconds": int},
                    "images": {"available": bool, "remaining_seconds": int},
                    "videos": {"available": bool, "remaining_seconds": int}
                },
                "limited_count": int,  # 受限配额数量
                "total_count": int,    # 总配额数量
                "is_expired": bool     # 账户是否过期/禁用
            }
        """
        # 检查账户是否过期或被禁用
        is_expired = self.config.is_expired() or self.config.disabled
        if is_expired:
            # 账户过期或被禁用，所有配额不可用
            quotas = {quota_type: {"available": False} for quota_type in QUOTA_TYPES}
            return {
                "quotas": quotas,
                "limited_count": len(QUOTA_TYPES),
                "total_count": len(QUOTA_TYPES),
                "is_expired": True
            }

        current_time = time.time()

        quotas = {}
        limited_count = 0
        expired_quotas = []  # 收集已过期的配额类型
        text_limited = False  # 对话配额是否受限

        # 第一遍：检查所有配额状态
        for quota_type in QUOTA_TYPES:
            if quota_type in self.quota_cooldowns:
                cooldown_time = self.quota_cooldowns[quota_type]
                # 检查冷却时间是否已过（按配额类型）
                elapsed = current_time - cooldown_time
                cooldown_seconds = self._get_quota_cooldown_seconds(quota_type)
                if elapsed < cooldown_seconds:
                    remaining = int(cooldown_seconds - elapsed)
                    quotas[quota_type] = {
                        "available": False,
                        "remaining_seconds": remaining
                    }
                    limited_count += 1
                    # 标记对话配额受限
                    if quota_type == "text":
                        text_limited = True
                else:
                    # 冷却时间已过，标记为待删除
                    expired_quotas.append(quota_type)
                    quotas[quota_type] = {"available": True}
            else:
                # 未检测到限流
                quotas[quota_type] = {"available": True}

        # 统一删除已过期的配额冷却
        for quota_type in expired_quotas:
            del self.quota_cooldowns[quota_type]

        # 如果对话配额受限，所有配额都标记为不可用（对话是基础功能）
        if text_limited:
            for quota_type in QUOTA_TYPES:
                if quota_type != "text" and quotas[quota_type].get("available", False):
                    quotas[quota_type] = {
                        "available": False,
                        "reason": "对话配额受限"
                    }
                    limited_count += 1

        return {
            "quotas": quotas,
            "limited_count": limited_count,
            "total_count": len(QUOTA_TYPES),
            "is_expired": False
        }


class MultiAccountManager:
    """多账户协调器"""
    def __init__(self, session_cache_ttl_seconds: int):
        self.accounts: Dict[str, AccountManager] = {}
        self.account_list: List[str] = []  # 账户ID列表 (用于轮询)
        self.current_index = 0
        self._cache_lock = asyncio.Lock()  # 缓存操作专用锁
        self._counter_lock = threading.Lock()  # 轮询计数器锁
        self._request_counter = 0  # 请求计数器
        self._last_account_count = 0  # 可用账户数量
        # 全局会话缓存：{conv_key: {"account_id": str, "session_id": str, "updated_at": float}}
        self.global_session_cache: Dict[str, dict] = {}
        self.cache_max_size = 1000  # 最大缓存条目数
        self.cache_ttl = session_cache_ttl_seconds  # 缓存过期时间（秒）
        # Session级别锁：防止同一对话的并发请求冲突
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._session_locks_lock = asyncio.Lock()  # 保护锁字典的锁
        self._session_locks_max_size = 2000  # 最大锁数量

    def _clean_expired_cache(self):
        """清理过期的缓存条目"""
        current_time = time.time()
        expired_keys = [
            key for key, value in self.global_session_cache.items()
            if current_time - value["updated_at"] > self.cache_ttl
        ]
        for key in expired_keys:
            del self.global_session_cache[key]
        if expired_keys:
            logger.info(f"[CACHE] 清理 {len(expired_keys)} 个过期会话缓存")

    def _ensure_cache_size(self):
        """确保缓存不超过最大大小（LRU策略）"""
        if len(self.global_session_cache) > self.cache_max_size:
            # 按更新时间排序，删除最旧的20%
            sorted_items = sorted(
                self.global_session_cache.items(),
                key=lambda x: x[1]["updated_at"]
            )
            remove_count = len(sorted_items) - int(self.cache_max_size * 0.8)
            for key, _ in sorted_items[:remove_count]:
                del self.global_session_cache[key]
            logger.info(f"[CACHE] LRU清理 {remove_count} 个最旧会话缓存")

    async def start_background_cleanup(self):
        """启动后台缓存清理任务（每5分钟执行一次）"""
        try:
            while True:
                await asyncio.sleep(300)  # 5分钟
                async with self._cache_lock:
                    self._clean_expired_cache()
                    self._ensure_cache_size()
        except asyncio.CancelledError:
            logger.info("[CACHE] 后台清理任务已停止")
        except Exception as e:
            logger.error(f"[CACHE] 后台清理任务异常: {e}")

    async def set_session_cache(self, conv_key: str, account_id: str, session_id: str):
        """线程安全地设置会话缓存"""
        async with self._cache_lock:
            self.global_session_cache[conv_key] = {
                "account_id": account_id,
                "session_id": session_id,
                "updated_at": time.time()
            }
            # 检查缓存大小
            self._ensure_cache_size()

    async def update_session_time(self, conv_key: str):
        """线程安全地更新会话时间戳"""
        async with self._cache_lock:
            if conv_key in self.global_session_cache:
                self.global_session_cache[conv_key]["updated_at"] = time.time()

    async def acquire_session_lock(self, conv_key: str) -> asyncio.Lock:
        """获取指定对话的锁（用于防止同一对话的并发请求冲突）"""
        async with self._session_locks_lock:
            # 清理过多的锁（LRU策略：删除不在缓存中的锁）
            if len(self._session_locks) > self._session_locks_max_size:
                # 只保留当前缓存中存在的锁
                valid_keys = set(self.global_session_cache.keys())
                keys_to_remove = [k for k in self._session_locks if k not in valid_keys]
                for k in keys_to_remove[:len(keys_to_remove)//2]:  # 删除一半无效锁
                    del self._session_locks[k]

            if conv_key not in self._session_locks:
                self._session_locks[conv_key] = asyncio.Lock()
            return self._session_locks[conv_key]

    def update_http_client(self, http_client):
        """更新所有账户使用的 http_client（用于代理变更后重建客户端）"""
        for account_mgr in self.accounts.values():
            account_mgr.http_client = http_client
            if account_mgr.jwt_manager is not None:
                account_mgr.jwt_manager.http_client = http_client

    def add_account(
        self,
        config: AccountConfig,
        http_client,
        user_agent: str,
        retry_policy: RetryPolicy,
        global_stats: dict,
    ):
        """添加账户"""
        manager = AccountManager(config, http_client, user_agent, retry_policy)
        # 从统计数据加载对话次数
        if "account_conversations" in global_stats:
            manager.conversation_count = global_stats["account_conversations"].get(config.account_id, 0)
        if "account_failures" in global_stats:
            manager.failure_count = global_stats["account_failures"].get(config.account_id, 0)
        self.accounts[config.account_id] = manager
        self.account_list.append(config.account_id)
        logger.info(f"[MULTI] [ACCOUNT] 添加账户: {config.account_id}")

    async def get_account(
        self,
        account_id: Optional[str] = None,
        request_id: str = "",
        required_quota_types: Optional[Iterable[str]] = None
    ) -> AccountManager:
        """获取账户 - Round-Robin轮询"""
        req_tag = f"[req_{request_id}] " if request_id else ""

        # 指定账户ID时直接返回
        if account_id:
            if account_id not in self.accounts:
                raise HTTPException(404, f"Account {account_id} not found")
            account = self.accounts[account_id]
            if not account.should_retry():
                raise HTTPException(503, f"Account {account_id} temporarily unavailable")
            if not account.are_quotas_available(required_quota_types):
                raise HTTPException(503, f"Account {account_id} quota temporarily unavailable")
            return account

        # 筛选可用账户
        available_accounts = [
            acc for acc in self.accounts.values()
            if (acc.should_retry() and
                not acc.config.is_expired() and
                not acc.config.disabled and
                acc.are_quotas_available(required_quota_types))
        ]

        if not available_accounts:
            raise HTTPException(503, "No available accounts")

        # 轮询选择
        with self._counter_lock:
            if len(available_accounts) != self._last_account_count:
                self._request_counter = random.randint(0, 999999)
                self._last_account_count = len(available_accounts)
            index = self._request_counter % len(available_accounts)
            self._request_counter += 1

        selected = available_accounts[index]
        selected.session_usage_count += 1

        logger.info(f"[MULTI] [ACCOUNT] {req_tag}选择账户: {selected.config.account_id} "
                    f"(索引: {index}/{len(available_accounts)}, 使用: {selected.session_usage_count})")
        return selected


# ---------- 配置管理 ----------

def save_accounts_to_file(accounts_data: list):
    """保存账户配置（仅数据库模式）。"""
    if not storage.is_database_enabled():
        raise RuntimeError("Database is not enabled")
    saved = storage.save_accounts_sync(accounts_data)
    if not saved:
        raise RuntimeError("Database write failed")


def load_accounts_from_source() -> list:
    """从环境变量或数据库加载账户配置。"""
    env_accounts = os.environ.get('ACCOUNTS_CONFIG')
    if env_accounts:
        try:
            accounts_data = json.loads(env_accounts)
            if accounts_data:
                logger.info(f"[CONFIG] 从环境变量加载配置，共 {len(accounts_data)} 个账户")
            else:
                logger.warning("[CONFIG] 环境变量 ACCOUNTS_CONFIG 为空")
            return accounts_data
        except Exception as e:
            logger.error(f"[CONFIG] 环境变量加载失败: {str(e)}")

    if storage.is_database_enabled():
        try:
            accounts_data = storage.load_accounts_sync()

            # 严格模式：数据库连接失败时抛出异常，阻止应用启动
            if accounts_data is None:
                logger.error("[CONFIG] ❌ 数据库连接失败")
                logger.error("[CONFIG] 请检查 DATABASE_URL 配置或网络连接")
                raise RuntimeError("数据库连接失败，应用无法启动")

            if accounts_data:
                logger.info(f"[CONFIG] 从数据库加载配置，共 {len(accounts_data)} 个账户")
            else:
                logger.warning("[CONFIG] 数据库中账户配置为空")
                logger.warning("[CONFIG] 如需迁移数据，请运行: python scripts/migrate_to_database.py")

            return accounts_data
        except RuntimeError:
            # 重新抛出 RuntimeError（数据库连接失败）
            raise
        except Exception as e:
            logger.error(f"[CONFIG] ❌ 数据库加载失败: {e}")
            raise RuntimeError(f"数据库加载失败: {e}")

    logger.error("[CONFIG] 未启用数据库且未提供 ACCOUNTS_CONFIG")
    return []


def get_account_id(acc: dict, index: int) -> str:
    """获取账户ID（有显式ID则使用，否则生成默认ID）"""
    return acc.get("id", f"account_{index}")


def load_multi_account_config(
    http_client,
    user_agent: str,
    retry_policy: RetryPolicy,
    session_cache_ttl_seconds: int,
    global_stats: dict
) -> MultiAccountManager:
    """从文件或环境变量加载多账户配置"""
    manager = MultiAccountManager(session_cache_ttl_seconds)

    accounts_data = load_accounts_from_source()

    for i, acc in enumerate(accounts_data, 1):
        # 验证必需字段
        required_fields = ["secure_c_ses", "csesidx", "config_id"]
        missing_fields = [f for f in required_fields if f not in acc]
        if missing_fields:
            raise ValueError(f"账户 {i} 缺少必需字段: {', '.join(missing_fields)}")

        config = AccountConfig(
            account_id=get_account_id(acc, i),
            secure_c_ses=acc["secure_c_ses"],
            host_c_oses=acc.get("host_c_oses"),
            csesidx=acc["csesidx"],
            config_id=acc["config_id"],
            expires_at=acc.get("expires_at"),
            disabled=acc.get("disabled", False),  # 读取手动禁用状态，默认为False
            mail_provider=acc.get("mail_provider"),
            mail_address=acc.get("mail_address"),
            mail_password=acc.get("mail_password") or acc.get("email_password"),
            mail_client_id=acc.get("mail_client_id"),
            mail_refresh_token=acc.get("mail_refresh_token"),
            mail_tenant=acc.get("mail_tenant"),
        )

        # 检查账户是否已过期（已过期也加载到管理面板）
        is_expired = config.is_expired()
        if is_expired:
            logger.warning(f"[CONFIG] 账户 {config.account_id} 已过期，仍加载用于展示")

        manager.add_account(config, http_client, user_agent, retry_policy, global_stats)
        if is_expired:
            manager.accounts[config.account_id].is_available = False

    if not manager.accounts:
        logger.warning(f"[CONFIG] 没有有效的账户配置，服务将启动但无法处理请求，请在管理面板添加账户")
    else:
        logger.info(f"[CONFIG] 成功加载 {len(manager.accounts)} 个账户")
    return manager


def reload_accounts(
    multi_account_mgr: MultiAccountManager,
    http_client,
    user_agent: str,
    retry_policy: RetryPolicy,
    session_cache_ttl_seconds: int,
    global_stats: dict
) -> MultiAccountManager:
    """Reload account config and preserve runtime cooldown/error state."""
    # Preserve stats + runtime state to avoid clearing cooldowns on reload.
    old_stats = {}
    for account_id, account_mgr in multi_account_mgr.accounts.items():
        old_stats[account_id] = {
            "conversation_count": account_mgr.conversation_count,
            "failure_count": account_mgr.failure_count,
            "is_available": account_mgr.is_available,
            "last_error_time": account_mgr.last_error_time,
            "last_cooldown_time": account_mgr.last_cooldown_time,
            "session_usage_count": account_mgr.session_usage_count,
            "quota_cooldowns": dict(account_mgr.quota_cooldowns),
        }

    # Clear session cache and reload config.
    multi_account_mgr.global_session_cache.clear()
    new_mgr = load_multi_account_config(
        http_client,
        user_agent,
        retry_policy,
        session_cache_ttl_seconds,
        global_stats
    )

    # Restore stats + runtime state.
    for account_id, stats in old_stats.items():
        if account_id in new_mgr.accounts:
            account_mgr = new_mgr.accounts[account_id]
            account_mgr.conversation_count = stats["conversation_count"]
            account_mgr.failure_count = stats.get("failure_count", 0)
            account_mgr.is_available = stats.get("is_available", True)
            account_mgr.last_error_time = stats.get("last_error_time", 0.0)
            account_mgr.last_cooldown_time = stats.get("last_cooldown_time", 0.0)
            account_mgr.session_usage_count = stats.get("session_usage_count", 0)
            account_mgr.quota_cooldowns = stats.get("quota_cooldowns", {})
            logger.debug(f"[CONFIG] Account {account_id} refreshed; runtime state preserved")

    logger.info(
        f"[CONFIG] Reloaded config; accounts={len(new_mgr.accounts)}; cooldown/error state preserved"
    )
    return new_mgr


def update_accounts_config(
    accounts_data: list,
    multi_account_mgr: MultiAccountManager,
    http_client,
    user_agent: str,
    retry_policy: RetryPolicy,
    session_cache_ttl_seconds: int,
    global_stats: dict
) -> MultiAccountManager:
    """更新账户配置（保存到文件并重新加载）"""
    save_accounts_to_file(accounts_data)
    return reload_accounts(
        multi_account_mgr,
        http_client,
        user_agent,
        retry_policy,
        session_cache_ttl_seconds,
        global_stats
    )


def delete_account(
    account_id: str,
    multi_account_mgr: MultiAccountManager,
    http_client,
    user_agent: str,
    retry_policy: RetryPolicy,
    session_cache_ttl_seconds: int,
    global_stats: dict
) -> MultiAccountManager:
    """删除单个账户"""
    if storage.is_database_enabled():
        deleted = storage.delete_accounts_sync([account_id])
        if deleted <= 0:
            raise ValueError(f"账户 {account_id} 不存在")
        return reload_accounts(
            multi_account_mgr,
            http_client,
            user_agent,
            retry_policy,
            session_cache_ttl_seconds,
            global_stats
        )

    accounts_data = load_accounts_from_source()

    filtered = [
        acc for i, acc in enumerate(accounts_data, 1)
        if get_account_id(acc, i) != account_id
    ]

    if len(filtered) == len(accounts_data):
        raise ValueError(f"账户 {account_id} 不存在")

    save_accounts_to_file(filtered)
    return reload_accounts(
        multi_account_mgr,
        http_client,
        user_agent,
        retry_policy,
        session_cache_ttl_seconds,
        global_stats
    )


def update_account_disabled_status(
    account_id: str,
    disabled: bool,
    multi_account_mgr: MultiAccountManager,
) -> MultiAccountManager:
    """更新账户的禁用状态（优化版：优先数据库直写）。"""
    if storage.is_database_enabled():
        updated = storage.update_account_disabled_sync(account_id, disabled)
        if not updated:
            raise ValueError(f"账户 {account_id} 不存在")
        if account_id in multi_account_mgr.accounts:
            multi_account_mgr.accounts[account_id].config.disabled = disabled
        return multi_account_mgr

    if account_id not in multi_account_mgr.accounts:
        raise ValueError(f"账户 {account_id} 不存在")
    account_mgr = multi_account_mgr.accounts[account_id]
    account_mgr.config.disabled = disabled

    accounts_data = load_accounts_from_source()
    for i, acc in enumerate(accounts_data, 1):
        if get_account_id(acc, i) == account_id:
            acc["disabled"] = disabled
            break

    save_accounts_to_file(accounts_data)

    status_text = "已禁用" if disabled else "已启用"
    logger.info(f"[CONFIG] 账户 {account_id} {status_text}")
    return multi_account_mgr


def bulk_update_account_disabled_status(
    account_ids: list[str],
    disabled: bool,
    multi_account_mgr: MultiAccountManager,
) -> tuple[int, list[str]]:
    """批量更新账户禁用状态，单次最多20个。"""
    if storage.is_database_enabled():
        updated, missing = storage.bulk_update_accounts_disabled_sync(account_ids, disabled)
        for account_id in account_ids:
            if account_id in multi_account_mgr.accounts:
                multi_account_mgr.accounts[account_id].config.disabled = disabled
        errors = [f"{account_id}: 账户不存在" for account_id in missing]
        status_text = "已禁用" if disabled else "已启用"
        logger.info(f"[CONFIG] 批量{status_text} {updated}/{len(account_ids)} 个账户")
        return updated, errors

    success_count = 0
    errors = []

    for account_id in account_ids:
        if account_id not in multi_account_mgr.accounts:
            errors.append(f"{account_id}: 账户不存在")
            continue
        account_mgr = multi_account_mgr.accounts[account_id]
        account_mgr.config.disabled = disabled
        success_count += 1

    accounts_data = load_accounts_from_source()
    account_id_set = set(account_ids)

    for i, acc in enumerate(accounts_data, 1):
        acc_id = get_account_id(acc, i)
        if acc_id in account_id_set:
            acc["disabled"] = disabled

    save_accounts_to_file(accounts_data)

    status_text = "已禁用" if disabled else "已启用"
    logger.info(f"[CONFIG] 批量{status_text} {success_count}/{len(account_ids)} 个账户")
    return success_count, errors


def bulk_delete_accounts(
    account_ids: list[str],
    multi_account_mgr: MultiAccountManager,
    http_client,
    user_agent: str,
    retry_policy: RetryPolicy,
    session_cache_ttl_seconds: int,
    global_stats: dict
) -> tuple[MultiAccountManager, int, list[str]]:
    """批量删除账户，单次最多20个。"""
    if storage.is_database_enabled():
        existing_ids = set(multi_account_mgr.accounts.keys())
        missing = [account_id for account_id in account_ids if account_id not in existing_ids]
        deleted = storage.delete_accounts_sync(account_ids)
        errors = [f"{account_id}: 账户不存在" for account_id in missing]
        if deleted > 0:
            multi_account_mgr = reload_accounts(
                multi_account_mgr,
                http_client,
                user_agent,
                retry_policy,
                session_cache_ttl_seconds,
                global_stats
            )
        logger.info(f"[CONFIG] 批量删除 {deleted}/{len(account_ids)} 个账户")
        return multi_account_mgr, deleted, errors

    errors = []
    account_id_set = set(account_ids)

    accounts_data = load_accounts_from_source()
    kept: list[dict] = []
    deleted_ids: list[str] = []

    for i, acc in enumerate(accounts_data, 1):
        acc_id = get_account_id(acc, i)
        if acc_id in account_id_set:
            deleted_ids.append(acc_id)
            continue
        kept.append(acc)

    missing = account_id_set.difference(deleted_ids)
    for account_id in missing:
        errors.append(f"{account_id}: 账户不存在")

    if deleted_ids:
        save_accounts_to_file(kept)
        multi_account_mgr = reload_accounts(
            multi_account_mgr,
            http_client,
            user_agent,
            retry_policy,
            session_cache_ttl_seconds,
            global_stats
        )

    success_count = len(deleted_ids)
    logger.info(f"[CONFIG] 批量删除 {success_count}/{len(account_ids)} 个账户")
    return multi_account_mgr, success_count, errors
