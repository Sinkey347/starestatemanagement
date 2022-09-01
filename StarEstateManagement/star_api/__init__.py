from django.core.cache import cache
from utils.constant import  REDIS_CLIENT

# 初始化缓存对象
cache.get_or_set('mysql', 0, 60*60*24)
cache.get_or_set('redis', 0, 60*60*24)
cache.get_or_set('id', 0, 60*60*24)
cache.get_or_set('phone', 0, 60*60*24)
cache.get_or_set('alluser', 0, 60*60*24*30)
# 用户登录次数排行每24小时更新
REDIS_CLIENT.zadd('login_ranking', {0: 0})
REDIS_CLIENT.expireat('login_ranking', 60*60*24)
# 登录方式记录每24小时更新
REDIS_CLIENT.expireat('id', 60*60*24)
REDIS_CLIENT.expireat('phone', 60*60*24)
