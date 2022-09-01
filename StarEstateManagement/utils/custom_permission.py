from rest_framework.permissions import BasePermission


class UserPermission(BasePermission):
    """
    Allows access only to authenticated users.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.pk)


class AdminPermission(BasePermission):
    """
    验证管理员权限
    """

    def has_permission(self, request, view):
        """
        :params:request:请求对象
        :params:view:视图类
        :return:Boolean:验证结果
        """
        return bool(request.user and (request.user.group == 2))
