from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import requests

from outlook_web import config
from outlook_web.repositories.settings import get_gptmail_api_key


def gptmail_request(
    method: str,
    endpoint: str,
    params: dict = None,
    json_data: dict = None,
) -> Optional[Dict]:
    """
    发送 GPTMail API 请求

    返回格式：
    - 成功：{"success": True, "data": {...}}
    - 失败：{"success": False, "error": "错误信息", "error_type": "错误类型", "details": "详细信息"}
    """
    try:
        url = f"{config.get_gptmail_base_url()}{endpoint}"
        api_key = get_gptmail_api_key()

        # 检查 API Key 是否配置
        if not api_key:
            return {
                "success": False,
                "error": "GPTMail API Key 未配置",
                "error_type": "CONFIG_ERROR",
                "details": "请在系统设置中配置 GPTMail API Key"
            }

        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }

        # 发送请求
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=json_data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, params=params, timeout=30)
        else:
            return {
                "success": False,
                "error": f"不支持的请求方法: {method}",
                "error_type": "METHOD_ERROR",
                "details": "仅支持 GET、POST、DELETE 方法"
            }

        # 处理响应
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {
                "success": False,
                "error": "API Key 无效或已过期",
                "error_type": "AUTH_ERROR",
                "details": f"HTTP {response.status_code}: 请检查 API Key 是否正确"
            }
        elif response.status_code == 403:
            return {
                "success": False,
                "error": "API 访问被拒绝",
                "error_type": "PERMISSION_ERROR",
                "details": f"HTTP {response.status_code}: 请检查 API Key 权限"
            }
        elif response.status_code == 429:
            return {
                "success": False,
                "error": "API 请求频率超限",
                "error_type": "RATE_LIMIT_ERROR",
                "details": f"HTTP {response.status_code}: 请稍后重试"
            }
        elif response.status_code >= 500:
            return {
                "success": False,
                "error": "GPTMail 服务暂时不可用",
                "error_type": "SERVER_ERROR",
                "details": f"HTTP {response.status_code}: 服务器错误，请稍后重试"
            }
        else:
            return {
                "success": False,
                "error": f"API 请求失败",
                "error_type": "HTTP_ERROR",
                "details": f"HTTP {response.status_code}: {response.text[:200]}"
            }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "API 请求超时",
            "error_type": "TIMEOUT_ERROR",
            "details": "请求超过 30 秒未响应，请检查网络连接或稍后重试"
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "success": False,
            "error": "无法连接到 GPTMail 服务",
            "error_type": "CONNECTION_ERROR",
            "details": f"网络连接失败: {str(e)[:200]}"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": "网络请求异常",
            "error_type": "REQUEST_ERROR",
            "details": f"请求失败: {str(e)[:200]}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": "未知错误",
            "error_type": "UNKNOWN_ERROR",
            "details": f"异常: {str(e)[:200]}"
        }


def generate_temp_email(prefix: str = None, domain: str = None) -> Tuple[Optional[str], Optional[str]]:
    """
    生成临时邮箱地址

    返回：
    - (email_addr, None) - 成功
    - (None, error_message) - 失败，包含详细错误信息
    """
    json_data = {}
    if prefix:
        json_data["prefix"] = prefix
    if domain:
        json_data["domain"] = domain

    if json_data:
        result = gptmail_request("POST", "/api/generate-email", json_data=json_data)
    else:
        result = gptmail_request("GET", "/api/generate-email")

    if not result:
        return None, "GPTMail API 请求失败"

    if result.get("success"):
        email = result.get("data", {}).get("email")
        if email:
            return email, None
        else:
            return None, "API 返回数据格式错误：缺少 email 字段"
    else:
        # 返回详细的错误信息
        error = result.get("error", "未知错误")
        error_type = result.get("error_type", "UNKNOWN")
        details = result.get("details", "")

        # 组合错误信息
        if details:
            error_message = f"{error}（{details}）"
        else:
            error_message = error

        return None, error_message


def get_temp_emails_from_api(email_addr: str) -> Optional[List[Dict]]:
    """从 GPTMail API 获取邮件列表"""
    result = gptmail_request("GET", "/api/emails", params={"email": email_addr})
    if result and result.get("success"):
        return result.get("data", {}).get("emails", [])
    return None


def get_temp_email_detail_from_api(message_id: str) -> Optional[Dict]:
    """从 GPTMail API 获取邮件详情"""
    result = gptmail_request("GET", f"/api/email/{message_id}")
    if result and result.get("success"):
        return result.get("data")
    return None


def delete_temp_email_from_api(message_id: str) -> bool:
    """从 GPTMail API 删除邮件"""
    result = gptmail_request("DELETE", f"/api/email/{message_id}")
    return bool(result and result.get("success", False))


def clear_temp_emails_from_api(email_addr: str) -> bool:
    """清空 GPTMail 邮箱的所有邮件"""
    result = gptmail_request("DELETE", "/api/emails/clear", params={"email": email_addr})
    return bool(result and result.get("success", False))
