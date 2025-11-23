import requests
import json
from django.conf import settings
from django.core.cache import cache
from .exceptions import BusinessException


class WeChatAPI:
    """微信API服务类"""

    @staticmethod
    def get_access_token():
        """
        获取微信access_token
        """
        cache_key = 'wechat_access_token'
        access_token = cache.get(cache_key)

        if not access_token:
            url = 'https://api.weixin.qq.com/cgi-bin/token'
            params = {
                'grant_type': 'client_credential',
                'appid': settings.WECHAT_CONFIG['APP_ID'],
                'secret': settings.WECHAT_CONFIG['APP_SECRET']
            }

            try:
                response = requests.get(url, params=params, timeout=10)
                data = response.json()

                if 'access_token' in data:
                    access_token = data['access_token']
                    expires_in = data.get('expires_in', 7200) - 300  # 提前5分钟过期
                    cache.set(cache_key, access_token, expires_in)
                else:
                    raise BusinessException(f"获取access_token失败: {data.get('errmsg', '未知错误')}")

            except requests.RequestException as e:
                raise BusinessException(f"微信API请求失败: {str(e)}")

        return access_token

    @staticmethod
    def code_to_session(code):
        """
        通过code获取用户openid和session_key
        """
        url = 'https://api.weixin.qq.com/sns/jscode2session'
        params = {
            'appid': settings.WECHAT_CONFIG['APP_ID'],
            'secret': settings.WECHAT_CONFIG['APP_SECRET'],
            'js_code': code,
            'grant_type': 'authorization_code'
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if 'openid' in data:
                return {
                    'openid': data['openid'],
                    'session_key': data.get('session_key', ''),
                    'unionid': data.get('unionid', '')
                }
            else:
                error_msg = data.get('errmsg', '未知错误')
                if data.get('errcode') == 40029:
                    raise BusinessException('无效的code')
                elif data.get('errcode') == 45011:
                    raise BusinessException('API调用太频繁，请稍后再试')
                else:
                    raise BusinessException(f'微信登录失败: {error_msg}')

        except requests.RequestException as e:
            raise BusinessException(f"微信API请求失败: {str(e)}")

    @staticmethod
    def get_user_phone_number(code):
        """
        获取用户手机号
        """
        access_token = WeChatAPI.get_access_token()
        url = f'https://api.weixin.qq.com/wxa/business/getuserphonenumber?access_token={access_token}'

        data = {
            'code': code
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()

            if result.get('errcode') == 0:
                phone_info = result.get('phone_info', {})
                return {
                    'phone_number': phone_info.get('phoneNumber', ''),
                    'pure_phone_number': phone_info.get('purePhoneNumber', ''),
                    'country_code': phone_info.get('countryCode', '')
                }
            else:
                raise BusinessException(f"获取手机号失败: {result.get('errmsg', '未知错误')}")

        except requests.RequestException as e:
            raise BusinessException(f"微信API请求失败: {str(e)}")

    @staticmethod
    def send_subscribe_message(openid, template_id, data, page=None):
        """
        发送订阅消息
        """
        access_token = WeChatAPI.get_access_token()
        url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}'

        message_data = {
            'touser': openid,
            'template_id': template_id,
            'data': data
        }

        if page:
            message_data['page'] = page

        try:
            response = requests.post(url, json=message_data, timeout=10)
            result = response.json()

            if result.get('errcode') == 0:
                return True
            else:
                # 记录错误但不抛出异常，避免影响主流程
                print(f"发送订阅消息失败: {result.get('errmsg')}")
                return False

        except requests.RequestException:
            return False

    @staticmethod
    def validate_content_security(content):
        """
        内容安全校验
        """
        access_token = WeChatAPI.get_access_token()
        url = f'https://api.weixin.qq.com/wxa/msg_sec_check?access_token={access_token}'

        data = {
            'content': content
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()

            if result.get('errcode') == 0:
                return True
            elif result.get('errcode') == 87014:
                return False  # 内容违规
            else:
                # 其他错误，默认通过
                return True

        except requests.RequestException:
            # 网络错误，默认通过
            return True

    @staticmethod
    def create_wxacode(scene, page=None, width=430, auto_color=False, line_color=None):
        """
        生成小程序码
        """
        access_token = WeChatAPI.get_access_token()
        url = f'https://api.weixin.qq.com/wxa/getwxacodeunlimit?access_token={access_token}'

        data = {
            'scene': scene,
            'width': width,
            'auto_color': auto_color
        }

        if page:
            data['page'] = page

        if line_color and not auto_color:
            data['line_color'] = line_color

        try:
            response = requests.post(url, json=data, timeout=10)

            # 检查是否是图片
            if response.headers.get('Content-Type') == 'image/jpeg':
                return response.content
            else:
                result = response.json()
                raise BusinessException(f"生成小程序码失败: {result.get('errmsg', '未知错误')}")

        except requests.RequestException as e:
            raise BusinessException(f"微信API请求失败: {str(e)}")