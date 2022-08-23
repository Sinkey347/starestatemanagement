from django.core.cache import cache
from utils.constant import DAY_DATA_TIME, REDIS_CLIENT

# 初始化缓存对象
cache.get_or_set('mysql', 0, DAY_DATA_TIME)
cache.get_or_set('redis', 0, DAY_DATA_TIME)
# 用户登录次数排行每24小时更新
REDIS_CLIENT.zadd('login_ranking', {0: 0})
REDIS_CLIENT.expireat('login_ranking', DAY_DATA_TIME)
# 登录方式记录每24小时更新
REDIS_CLIENT.expireat('id', DAY_DATA_TIME)
REDIS_CLIENT.expireat('phone', DAY_DATA_TIME)