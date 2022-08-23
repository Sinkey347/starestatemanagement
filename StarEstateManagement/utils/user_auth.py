import ujson
from django.core.cache import cache
from rest_framework import exceptions
from django.utils.translation import gettext_lazy as _
from rest_framework.authentication import TokenAuthentication

from star_db.models import User


class UserTokenAuthentication(TokenAuthentication):
    """
    用户token认证类
    """
    def authenticate_credentials(self, key):
        """
        token认证
        :param key: token
        :return: 用户对象和token值
        """
        # 获取token的用户信息
        user_data = cache.get(key)
        # 如果有数据则说明是有效的token
        if user_data:
            # 反序列化缓存数据
            user_data = ujson.loads(user_data)
            # 封装user对象
            user = User()
            for key in user_data:
                setattr(user, key, user_data.get(key))
            return user, key
        # 如果获取不到缓存数据则说明是无效的token
        raise exceptions.AuthenticationFailed(_('Invalid token.'))
