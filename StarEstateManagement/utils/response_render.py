from collections import OrderedDict
from datetime import datetime

from rest_framework.renderers import JSONRenderer
from rest_framework.utils.serializer_helpers import ReturnDict

class CustomRenderer(JSONRenderer):
    """
    json响应渲染类
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        :param data: 待渲染的需要数据
        :param accepted_media_type: 内容协商格式
        :param renderer_context: 响应上下文
        :return: 渲染后的json响应对象
        """
        if renderer_context:
            # 获取响应码
            res_code = renderer_context.get("response").status_code
            # 初始化响应数据格式
            ret = {
                "code": 1 if res_code >= 400 or (data and data.get("code")) else 0
            }
            ret['msg'] = 'error' if ret.get('code') else 'success'
            # 单条数据返回
            if isinstance(data, ReturnDict):
                ret["data"] = data
            # 多条数据返回
            elif isinstance(data, OrderedDict):
                ret["data"] = {
                    "total": data.get("count"),
                    "list": data.get("results")
                }
            # 如果响应数据有文本则写入data
            elif data:
                # 如果包含token则写入data
                if data.get("token"):
                    ret["token"] = data.pop("token")
                else:
                    ret['data'] = data
            return super().render(ret, accepted_media_type, renderer_context)


