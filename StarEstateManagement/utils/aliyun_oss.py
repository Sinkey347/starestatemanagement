import oss2
from django.conf import settings


# 阿里云账号AccessKey拥有所有API的访问权限，风险很高。强烈建议您创建并使用RAM用户进行API访问或日常运维，请登录RAM控制台创建RAM用户。
auth = oss2.Auth(settings.ACCESSKEY_ID, settings.ACCESSKEY_SECRET)

# 填写自定义域名，例如example.com。
cname = '你的域名'

# 填写Bucket名称，并设置is_cname=True来开启CNAME。CNAME是指将自定义域名绑定到存储空间。
bucket = oss2.Bucket(auth, cname, 'star-user-avatar', is_cname=True, connect_timeout=60)
