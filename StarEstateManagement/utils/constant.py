import os
import datetime
from django.conf import settings
from django.core.cache import cache

REDIS_CLIENT = cache._cache.get_client()
AVATAR_DEFAULT_IMAGE = "http://oss.zhaoyixuan.cn/media/image/default/avatar.png"  # 头像默认图片
REDIS_SAVE_TIME = 60 * 60 * 2
DATA_FILE_PATH = os.path.join(settings.BASE_DIR, 'data.csv')
DAY_FILE_PATH = os.path.join(settings.BASE_DIR, 'day_data.csv')
DAY_DATA_TIME = 60 * 60 * 24
NOW_DAY = datetime.datetime.now().strftime('%Y-%m-%d')
NOW_TIME = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
