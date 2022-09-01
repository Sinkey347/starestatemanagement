import os
import datetime
from django.conf import settings
from django.core.cache import cache

REDIS_CLIENT = cache._cache.get_client()
AVATAR_DEFAULT_IMAGE = "https://oss.zhaoyixuan.cn/media/image/default/avatar.png"  # 头像默认图片
PUBLICITY_DEFAULT_IMAGE = 'https://oss.zhaoyixuan.cn/media/image/default/notice.png'  # 公告默认图片
REDIS_SAVE_TIME = 60 * 60 * 2
DAY_DATA_TIME = 60 * 60 * 24
NOW_DAY = datetime.datetime.now().strftime('%Y-%m-%d')
NOW_TIME = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
