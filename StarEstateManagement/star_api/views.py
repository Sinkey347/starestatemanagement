import binascii
import datetime
import os
import random
import time
import ujson
import xlwt
from io import BytesIO

from django.conf import settings
from django_filters.views import FilterView
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.db.models import F, Q, Count
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.authentication import get_authorization_header
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action, permission_classes
from utils.custom_pagination import CommentsPagination
from utils.custom_permission import AdminPermission, UserPermission
from utils.aliyun_oss import bucket
from utils.custom_search import UserFilter, ServiceFilter, ActivityApplyFilter, PublicityFilter, RepairsFilter, \
    EvaluateFilter, CommentsFilter, PaymentFilter, UserPaymentFilter, ParkingFilter, HouseFilter, MessageFilter
from utils.send_login_code import SendSms
from .serializer import *


@receiver([post_save, post_delete])
def change_cache(sender, instance, *args, **kwargs):
    """
    当模型对象执行save或delete后执行该方法
    :param sender: 当前模型对象
    :param instance: 当前实例对象
    :param args: 不定长参数
    :param kwargs: 关键字参数
    :return:
    """
    cache.get_or_set('mysql', 0, 60 * 60 * 24)
    cache.get_or_set('redis', 0, 60 * 60 * 24)
    cache.incr('mysql')
    cache.incr('redis')
    if sender.__name__ == 'Parking' or sender.__name__ == 'House':
        cache.delete(sender.__name__.lower())


# 用户信息数据模型器类
class UserModelViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserModelSerializers
    filterset_class = UserFilter

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        # 新增用户，社区总人数+1
        cache.incr('all_user')
        return Response({'code': 0}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        用户信息修改
        """
        # 如果要修改信息的用户和当前用户不一致且当前用户不是管理员则不允许修改
        if request.user.pk != self.get_object().pk and request.user.group != 2:
            return Response({'code': 1}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        # 删除用户，社区总人数-1
        cache.decr('all_user')
        return Response({'code': 0}, status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=False, url_path='worker', permission_classes=[AdminPermission])
    def get_worker(self, request):
        '''
        获取可执行任务的维修师傅的工号和名字
        :param request:请求对象
        :return:维修师傅信息的json数据
        '''
        # 返回用户组为1且没接任务的工人
        worker_list = self.get_queryset().filter(Q(group=1) & (Q(task_id=0)))
        data = {
            'code': 0,
            'list': self.get_serializer(worker_list, many=True, fields=('id', 'name')).data
        }
        return Response(data)

    @action(methods=['get'], detail=False, url_path='check')
    def check_user(self, request):
        '''
        校验用户权限
        :param request:请求对象
        :return: 校验结果
        '''
        try:
            # 根据当前用户的id获取最新用户组信息
            group = self.get_queryset().get(id=request.user.id).group
            # 如果是管理员则正常返回200
            if group == 2:
                return Response({'code': 0}, status=status.HTTP_200_OK)
            # 如果不是管理员则返回403
            return Response({'code': 1}, status=status.HTTP_403_FORBIDDEN)
        # 如果用户不存在则返回401
        except User.DoesNotExist:
            return Response({'code': 1}, status=status.HTTP_401_UNAUTHORIZED)
            

    @action(methods=['get'], detail=False, url_path='data', permission_classes=[AdminPermission])
    def get_data(self, request):
        '''
        用于获取今日用户数据信息
        :param request: 请求对象
        :return: 返回需要的用户数据信息
        '''
        user_group = ['普通用户', '维修师傅', '管理员']
        # 统计手机号登录和账号登录的用户数
        phone_login = cache.get('phone', 0)
        id_login = cache.get('id', 0)
        res = {
            'code': 0,
            # 获取登录用户信息
            'login': {
                '账号登录': id_login,
                '手机号登录': phone_login,
                '今日登录人数': id_login + phone_login
            },
            # 获取用户类型信息
            'group': {
                user_group[item['group']]: item['num'] for item in
                self.get_queryset().values('group').annotate(num=Count('*'))
            },
            # 如果获取用户活跃度排名信息并格式化{'username':123456, 'name':'张三', 'score':1}
            'ranking': [
                dict(ujson.loads(item[0]), **item[1]) for item in REDIS_CLIENT.zrange('login_ranking', 0, -1, desc=True,
                                                                                      withscores=True,
                                                                                      score_cast_func=lambda x: {
                                                                                          'score': x.decode('utf-8')})
            ]
        }
        return Response(res)

    @action(methods=['get'], detail=False, url_path='info')
    def get_info(self, request):
        '''
        根据token获取用户个人信息
        :param request: 请求对象
        :return: 包含用户信息的JSON数据
        '''
        # 获取指定当前用户信息并进行序列化
        return Response(self.get_serializer(self.get_queryset().get(username=request.user.username)).data)

    @action(methods=['get'], detail=False, url_path='id', permission_classes=[AdminPermission])
    def get_id(self, request):
        '''
        获取全部用户的姓名和id
        :param request: 请求对象
        :return: 包含用户信息的JSON数据
        '''
        # 获取指定当前用户信息并进行序列化
        res = {
            'code': 0,
            'data': {item['username']: item['id'] for item in self.get_queryset().values('id', 'username')}
        }
        return Response(res)

    @action(methods=['post'], detail=False, url_path='avatars')
    def upload_avatar(self, request):
        """
        上传用户头像
        :param request: 请求对象
        :return: 请求响应对象
        """
        # 获取文件对象
        avatar = request.FILES.get('avatar')
        res = {
            'code': 1
        }
        # 如果文件对象存在
        if avatar:
            # 获取文件格式
            filetype = '.png' if avatar.content_type == 'image/png' else '.jpg'
            # 拼接文件名
            filename = f'{request.user.username}{avatar.name[:avatar.name.rfind(".")]}' + filetype
            # 将文件上传oss并获取响应结果
            res = bucket.put_object(f'media/avatar/{filename}', avatar.file)
            # 如果响应状态码=200则上传成功更新用户头像
            if res.status == 200:
                res = {'code': 0, 'avatar': settings.OSS_HTTPS_URL + f'media/avatar/{filename}'}
        return Response(res, status=status.HTTP_201_CREATED)


# 用户服务报修数据模型器类
class UserServiceModelViewSet(ModelViewSet, FilterView):
    queryset = UserService.objects.all()
    serializer_class = UserServiceSerializers
    filterset_class = ServiceFilter

    def get_queryset(self):
        # 只返回当前用户相关的数据
        return UserService.objects.filter(username=self.request.user)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        # 获取删除对象
        instance = self.get_object()
        super().destroy(request, *args, **kwargs)
        try:
            # 如果任务状态为0则说明未被处理此时需要删除后台请求数据
            if instance.status != 6:
                # 如果删除的报修任务类型是A则说明是活动申请
                if instance.type == 'A':
                    # 将后台活动申请的记录也删除
                    ActivityApply.objects.get(id=instance.order_id, username_id=request.user.pk).delete()
                else:
                    # 否则将后台报修申请记录删除
                    RepairsApply.objects.get(username_id=request.user.pk, id=instance.order_id).delete()
            else:
                # 如果是反馈中则删除反馈记录
                Evaluate.objects.filter(username_id=request.user.pk, name=instance.name).delete()
        except:
            # 如果没有找到则说明不存在，不处理
            pass
        return Response({'code': 0}, status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'], detail=False, url_path='exists')
    def exists(self, request):
        '''
        用于判断订单反馈时判断订单是否存在
        :param request: 请求对象
        :return: 包含判断结果的JSON响应数据
        '''
        try:
            # 获取订单类型
            type = request.query_params.get('order_type')
            # 获取订单号
            order_id = request.query_params.get('id')
            # 根据类型指定过滤条件
            queryset_filter = Q(type='A') if type == '1' else ~Q(type='A')
            # 尝试根据传入的订单id获取与当前用户匹配的用户服务记录
            self.get_queryset().get(Q(order_id=order_id) & queryset_filter & Q(username__id=request.user.pk))
        except UserService.DoesNotExist:
            # 如果找不到则返回1表示不存在
            return Response({'code': 1})
        # 否则返回0表示存在
        return Response({'code': 0})


# 活动申请数据模型器类
class ActivityApplyModelViewSet(ModelViewSet):
    queryset = ActivityApply.objects.all()
    serializer_class = ActivityApplySerializers
    filterset_class = ActivityApplyFilter

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            # 获取申请的活动对象
            activity = Publicity.objects.get(id=request.data.get('id'))
            # 如果活动的已参与人数小于活动要求人数
            if activity.join + 1 < activity.need:
                # 创建用户活动申请记录
                request.data['username'] = request.user.pk
                request.data['publicity'] = request.data.get('id')
                res = super().create(request, *args, **kwargs)
                # 创建一条用户服务申请记录
                UserService.objects.create(username_id=request.user.pk, name=res.data.get('p_name'),
                                           order_id=res.data.get('id'), type='A')
                data = {'code': 0}
            # 如果活动已参与人数大于等于获取要求人数
            else:
                # 返回申请失败信息
                data = {'code': 1}
        except Publicity.DoesNotExist:
            # 如果活动不存在返回申请失败信息
            data = {'code': 1}
        return Response(data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        # 如果同意请求将活动状态设置为4即已完成
        if request.data.get('status') == 4:
            # 活动参与人数+1
            Publicity.objects.filter(id=request.data.get('publicity')).update(join=F('join') + 1)
        # 更新用户记录的活动状态
        UserService.objects.filter(order_id=self.get_object().id).update(status=request.data.get('status'))
        return Response({'code': 0})

    def destroy(self, request, *args, **kwargs):
        # 如果请求已被受理则需要管理员权限才能删除
        if self.get_object().status and request.user.group != 2:
            return Response({'code': 1}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


# 社区公示数据模型器类
class PublicityModelViewSet(ModelViewSet):
    queryset = Publicity.objects.all()
    serializer_class = PublicitySerializers
    filterset_class = PublicityFilter

    def list(self, request, *args, **kwargs):
        # 获取社区公告中结束日期小于当前日期的公告，设置为1即过期状态
        Publicity.objects.filter(end__lt=datetime.datetime.utcnow()).update(status=1)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        # 发布通知时将通知记录与用户绑定
        request.data['username'] = request.user.pk
        # 获取公告标题
        title = request.data.get('title')
        # 如果type=2则说明是收费通知，此时为标题添加月份，否则不做处理
        request.data['title'] = f'{datetime.datetime.utcnow().month}月份' + title \
            if request.data.get('type') == 2 else title
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.data.get('oper'):
            good_status = REDIS_CLIENT.getbit(f'publicity{request.data.get("id")}', request.user.pk)
            if not good_status:
                # 如果是用户点赞则获取当前元素对象
                instance = self.get_queryset().get(pk=request.data.get('id'))
                # 计算点赞文章截止日期7天后的时间戳
                end_timestamp = time.mktime((instance.end + datetime.timedelta(weeks=1)).timetuple())
                # 将文章id位图中，用户id对应的位置设置为1，表示用户点赞该位置
                REDIS_CLIENT.setbit(f'publicity{request.data.get("id")}', request.user.pk, request.data.get('num'))
                # 设置过期时间
                REDIS_CLIENT.expireat(f'publicity{request.data.get("id")}', int(end_timestamp))
                return Response({'code': 0, 'good': REDIS_CLIENT.bitcount(f'publicity{request.data.get("id")}')})
            return Response({'code': 1})
        return super().update(request, *args, **kwargs)

    @action(methods=['get'], detail=False, url_path='progress', permission_classes=[AdminPermission])
    def get_progress(self, request):
        '''
        获取活动参与进度、缴费参与进度
        :param request: 请求对象
        :return: 包含活动参与进度或缴费参与进度的JSON数据响应对象
        '''
        data = {
            'code': 0,
            'list': []
        }
        data_key = request.query_params.get('data_key')
        match data_key:
            # 如果data_key==0说明需要获取活动参与信息
            case '0':
                # 返回各活动的标题、参与人数、需要人数来计算活动参与率
                data['list'] = self.get_serializer(self.get_queryset().filter(type=1), many=True,
                                                   fields=('title', 'join', 'need')).data
            # 如果data_key==1说明需要获取缴费情况
            case '1':
                # 返回各缴费项目的标题、参与人数、社区总人数来计算活动参与率
                data['list'] = self.get_serializer(self.get_queryset().filter(type=2), many=True,
                                                   fields=('title', 'join', 'all')).data
        return Response(data)

    @action(methods=['get'], detail=False, url_path='activity')
    def get_activity(self, request):
        '''
        获取首页社区活动内容数据
        :param request: 请求对象
        :return: 包含社区活动信息的缓存JSON数据响应对象
        '''
        data = {
            'code': 0,
            'list': self.get_serializer(self.get_queryset().filter(type=1), many=True,
                                        fields=('id', 'img', 'type', 'title', 'good', 'create_time')).data
        }
        return Response(data)

    @action(methods=['get'], detail=False, url_path='notice')
    def get_notice(self, request):
        '''
        获取首页通知公告内容数据
        :param request: 请求对象
        :return: 包含通知公告信息的缓存JSON数据响应对象
        '''
        data = {
            'code': 0,
            'list': self.get_serializer(self.get_queryset().filter(~Q(type=1)), many=True,
                                        fields=('id', 'img', 'type', 'title', 'good', 'create_time')).data
        }
        return Response(data)

    @action(methods=['get'], detail=False, url_path='list')
    def get_activity_list(self, request):
        '''
        获取可报名活动列表
        :param request: 请求对象
        :return: 包含可报名活动信息的JSON数据响应对象
        '''
        data = {
            'code': 0,
            'list': self.get_serializer(self.get_queryset().filter(Q(type=1) & Q(join__lt=F('need'))), many=True,
                                        fields=('id', 'title')).data
        }
        return Response(data)

    @action(methods=['get'], detail=False, url_path='ranking', permission_classes=[AdminPermission])
    def activity_ranking(self, request):
        '''
        获取所有活动对应的参与人数
        :param request: 请求对象
        :return: 包含活动参与人数信息的JSON数据响应对象
        '''
        data = {
            'code': 0,
            # 根据活动参与人数倒序返回活动标题和参与人数信息
            'list': self.get_serializer(self.get_queryset().filter(type=1).order_by('-join'), many=True,
                                        fields=('title', 'join')).data
        }
        return Response(data)

    @action(methods=['post'], detail=False, url_path='images', permission_classes=[AdminPermission])
    def upload_images(self, request):
        """
        上传公示图片
        :param request: 请求对象
        :return: 请求响应对象
        """
        # 获取文件对象
        image = request.FILES.get('image')
        # 获取数据库最后一个id
        queryset = self.get_queryset().order_by('-id')
        id = queryset[0].id if queryset else 0
        res = {
            'code': 1
        }
        # 如果文件对象存在
        if image:
            # 获取文件格式
            filetype = '.png' if image.content_type == 'image/png' else '.jpg'
            # 将文件上传oss并获取响应结果
            res = bucket.put_object(f'media/image/{id + 1}' + filetype, image.file)
            # 如果响应状态码=200则上传成功更新活动图片
            if res.status == 200:
                res = {'code': 0, 'img_url': settings.OSS_HTTPS_URL + f'media/image/{id + 1}' + filetype}
        return Response(res, status=status.HTTP_201_CREATED)


# 报修申请数据模型器类
class RepairsApplyModelViewSet(ModelViewSet):
    queryset = RepairsApply.objects.all()
    serializer_class = RepairsApplySerializers
    filterset_class = RepairsFilter


    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # 将申请人与申请记录绑定
        request.data['username'] = request.user.pk
        # 获取维修申请创建完后的对象数据
        res = super().create(request, *args, **kwargs)
        # 创建用户报修申请记录
        UserService.objects.create(username_id=request.user.pk, name=request.data.get('name'),
                                   order_id=res.data.get('id'), type=res.data.get('type'))
        return Response({'code': 0}, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        # 如果请求已被受理则需要管理员权限才能删除
        if self.get_object().status and request.user.group != 2:
            return Response({'code': 1}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


# 评价反馈数据模型器类
class EvaluateModelViewSet(ModelViewSet):
    queryset = Evaluate.objects.all()
    serializer_class = EvaluateSerializers
    filterset_class = EvaluateFilter

    def create(self, request, *args, **kwargs):
        request.data['username'] = request.user.pk
        # 获取当前星期数
        request.data['weekday'] = datetime.datetime.utcnow().isoweekday()
        data_key = request.data.pop('data_key')  # 0表示服务反馈，1表示缴费反馈
        obj = UserPayment if data_key else UserService
        # 如果传入了分数则说明是评价
        if request.data.get('score'):
            # 根据传入的记录id把对应任务状态改为7表示已评价，分数改为传入的分数
            obj.objects.filter(id=request.data.get('record_id')).update(status=7, score=request.data.get('score'))
        else:
            order_type = request.data.get('order_type')
            # 如果是反馈则获取反馈任务对象
            queryset = obj.objects.filter(order_id=request.data.get('record_id'))
            # 如果order_type==1则说明是活动报名的反馈
            if order_type == 1:
                queryset = queryset.filter(type='A')
            # 否则是故障维修的反馈
            elif order_type == 0:
                queryset = queryset.filter(~Q(type='A'))
            # 修改任务状态为6表示反馈中
            queryset.update(status=6)
            # 将反馈任务名记录
            request.data['name'] = queryset.first().name
        return super().create(request, *args, **kwargs)

    @action(methods=['get'], detail=False, url_path='data', permission_classes=[AdminPermission])
    def get_data(self, request):
        '''
        获取今日各类评价数据
        :param request: 请求对象
        :return: 包含今日评价信息的JSON数据响应对象
        '''
        # 初始化评价数据
        evaluate_list = {
            'praise': [0, 0, 0, 0, 0, 0, 0],
            'general': [0, 0, 0, 0, 0, 0, 0],
            'negative': [0, 0, 0, 0, 0, 0, 0]
        }
        data = {
            'code': 0,
            'list': evaluate_list
        }
        # 获取7天内的评价数据的星期数和分数
        evaluates = self.get_queryset().filter(create_time__gte=datetime.datetime.utcnow() - datetime.timedelta(weeks=1)
                                               , type=0).values_list('weekday', 'score')
        # 遍历评价数据按分数和星期数计数
        for item in list(evaluates):
            # 如果星期数为7则改为0
            weekday = item[0] if item[0] < 7 else 0
            # 分数小于3则说明是差评
            if item[1] < 3:
                # 修改评价等级数据对应星期的评价量
                evaluate_list['negative'][weekday] += 1
            # 分数大于等于3小于5说明是一般
            elif 3 <= item[1] < 5:
                # 修改评价等级数据对应星期的评价量
                evaluate_list['general'][weekday] += 1
            # 分数等于5说明是好评
            else:
                # 修改评价等级数据对应星期的评价量
                evaluate_list['praise'][weekday] += 1
        return Response(data)


# 评论留言模型器类
class CommentsModelViewSet(ModelViewSet):
    pagination_class = CommentsPagination
    queryset = Comments.objects.all()
    serializer_class = CommentsSerializers
    filterset_class = CommentsFilter

    def create(self, request, *args, **kwargs):
        # 如果是评论
        if request.data.get('type'):
            try:
                # 尝试获取父评论对象
                comments = self.get_queryset().get(id=request.data.get('father_id'))
                # 记录父评论的发布人
                replay_name = comments.username.username
            except Comments.DoesNotExist:
                replay_name = None
            # 获取评论的公示对象
            publicity = Publicity.objects.filter(id=request.data.get('page_id')).first()
            # 记录公示名
            page_name = publicity.title if publicity else None
            Comments.objects.create(username_id=request.user.id, type=request.data.get('type'),
                                    page_id=request.data.get('page_id'), page_name=page_name, replay_name=replay_name,
                                    father_id=request.data.get('father_id'), comment=request.data.get('comment'))
        # 如果是留言
        else:
            # 创建留言记录
            Comments.objects.create(username_id=request.user.id, type=request.data.get('type'),
                                    comment=request.data.get('comment'))
        return Response({'code': 0, 'total': self.get_queryset().count()}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        # 查找与它相关联的评论数据并一起屏蔽
        self.get_all_comments([request.data.get('id')], 'shield')
        return Response({'code': 0})

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        # 查找与它相关联的评论数据并一起删除
        self.get_all_comments([request.query_params.get('id')], 'delete')
        return Response({'code': 0})

    def get_all_comments(self, f_id_list, oper):
        '''
        递归找出指定评论相关的子评论
        :param f_id_list: 父评论id列表
        :param oper: 要进行的操作
        :return: None 跳出递归
        '''
        # 下一批父id的列表
        id_list = []
        if f_id_list:
            # 获取父id在目标id里的评论对象
            queryset = self.get_queryset().filter(father_id__in=f_id_list)
            for instance in queryset:
                # 将删除的元素id加入作为新的父id列表再查找
                id_list.append(instance.id)
                # 如果是屏蔽操作
                if oper == 'shield':
                    # show设置为不可展示
                    instance.show = 0
                    # 状态设为0表示已屏蔽
                    instance.status = 0
                    # 保存修改
                    instance.save()
                else:
                    # 如果是删除操作则删除对象
                    instance.delete()
            # 递归查找相关的评论
            self.get_all_comments(id_list, oper)
        else:
            return None


# 资金收缴数据模型器类
class PaymentModelViewSet(ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializers
    filterset_class = PaymentFilter

    # 开启事务提交
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        request.data['username'] = request.user.pk
        buy_type = request.data.get('type')
        res = super().create(request, *args, **kwargs)
        # 如果是购买车位或购买房屋
        if buy_type >= 4:
            # 如果是房屋购买则在房屋表添加一条使用记录
            if buy_type == 4:
                House.objects.create(username_id=request.user.pk, payment_id=res.data.get('id'),
                                     house_id=res.data.get('name')[0:5], area_code=res.data.get('name')[0],
                                     status=res.data.get('status'))
            # 如果是车位购买则在车位表添加一条使用记录
            elif buy_type == 5:
                Parking.objects.create(username_id=request.user.pk, payment_id=res.data.get('id'),
                                       parking_lot_id=res.data.get('name')[0:5], area_code=res.data.get('name')[0],
                                       status=res.data.get('status'))
            # 创建用户支付记录
            UserPayment.objects.create(username_id=request.user.pk, money=res.data.get('money'),
                                       order_id=res.data.get('id'), name=res.data.get('name'),
                                       status=res.data.get('status'))
        else:
            # 如果是社区缴费只要更新缴费状态即可
            Publicity.objects.filter(title=res.data.get('name')).update(join=F('join') + 1)
            # 将对应的用户缴费记录设置为3表示已缴费并写入订单号
            UserPayment.objects.filter(username_id=request.user.pk, name=res.data.get('name')). \
                update(status=3, order_id=res.data.get('id'))
        return Response({'code': 0}, status=status.HTTP_201_CREATED)

    @action(methods=['get'], detail=False, url_path='data', permission_classes=[AdminPermission])
    def get_data(self, request):
        '''
        获取今日社区费用缴费情况数据
        :param request: 请求对象
        :return: 包含今日收费数据的JSON数据响应对象
        '''
        # 按缴费记录类型进行分组再统计各组的缴费人数
        payment_group = self.get_queryset().extra(select={'name': 'type'}).values('name').annotate(value=Count('*'))
        data = {
            'code': 0,
            'list': payment_group,
            'total': cache.get('all_user')
        }
        return Response(data)


# 用户缴费情况数据模型器类
class UserPaymentsModelViewSet(ModelViewSet):
    queryset = UserPayment.objects.all()
    serializer_class = UserPaymentSerializers
    filterset_class = UserPaymentFilter

    def get_queryset(self):
        # 只返回当前用户相关的数据
        return UserPayment.objects.filter(username=self.request.user)

    def list(self, request, *args, **kwargs):
        # 获取本月收费款项的id列表
        month_payment = Publicity.objects.filter(create_time__month=datetime.datetime.utcnow().month, type=2)
        payment_dict = {'水费': 0, '电费': 1, '物业费': 2, '燃气费': 3}
        for task in month_payment:
            # 获取后台缴费记录
            payment = Payment.objects.filter(name=task.title, username_id=request.user.id)
            # 获取前台待缴费款项
            user_payment = UserPayment.objects.filter(username_id=request.user.id, name=task.title)
            # 如果后台不存在缴费记录且用户前台没有待缴费款项则创建一条待缴费记录
            if not payment and not user_payment:
                # 获取缴费类型
                money_type = payment_dict.get(task.title[task.title.find('份') + 1:])
                # 创建待缴费款项
                UserPayment.objects.create(username_id=request.user.id, money=task.money, name=task.title,
                                           type=money_type)
        return super().list(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        # 如果是反馈中则删除后台反馈记录
        if self.get_object().status == 6:
            Evaluate.objects.filter(username_id=request.user.pk, name=self.get_object().name).delete()
        return super().destroy(request, *args, **kwargs)

    @action(methods=['get'], detail=False, url_path='exists')
    def exists(self, request):
        '''
        用于订单反馈时判断订单号是否存在
        :param request: 请求对象
        :return: 判断结果
        '''
        try:
            # 尝试根据传入的订单号查找当前用户相关的订单
            self.get_queryset().get(Q(order_id=request.query_params.get('id')) & Q(username_id=request.user.pk))
        except:
            # 如果找不到则说明订单不存在
            return Response({'code': 1})
        # 否则说明订单存在
        return Response({'code': 0})


# 车位使用数据模型器类
class ParkingModelViewSet(ModelViewSet):
    queryset = Parking.objects.all()
    serializer_class = ParkingSerializers
    filterset_class = ParkingFilter

    def create(self, request, *args, **kwargs):
        # 只允许自己的名义购买车位
        request.data['username'] = request.user.pk
        return super().create(request, *args, **kwargs)

    @action(methods=['get'], detail=False, url_path='progress', permission_classes=[AdminPermission])
    def get_progress(self, request):
        '''
        获取各区车位使用数据百分比
        :param request: 请求对象
        :return: 返回包含各区车位使用情况百分比的JSON数据响应对象
        '''
        # 获取各区车位使用数目并格式化
        parking_data = {
            item['area_code']: item['num'] for item in self.get_queryset().values('area_code').annotate(num=Count('*'))
        }
        # # 获取全部车位使用数目
        parking_data['all'] = self.get_queryset().count()
        data = {
            'code': 0,
            'list': parking_data
        }
        return Response(data)

    @action(methods=['get'], detail=False, url_path='data', permission_classes=[AdminPermission])
    def get_data(self, request):
        '''
        获取各区车位使用情况
        :param request: 请求对象
        :return: 包含各区车位使用情况的JSON数据响应对象
        '''
        # 获取各区车位使用数目
        parking_list = self.get_queryset().extra(select={'name': 'area_code'}).values('name').annotate(value=Count('*'))
        data = {
            'code': 0,
            'list': parking_list
        }
        return Response(data)


# 获取房屋使用数据模型器类
class HouseModelViewSet(ModelViewSet):
    queryset = House.objects.all()
    serializer_class = HouseSerializers
    filterset_class = HouseFilter

    def create(self, request, *args, **kwargs):
        # 只允许自己的名义购买房屋
        request.data['username'] = request.user.pk
        return super().create(request, *args, **kwargs)

    @action(methods=['get'], detail=False, url_path='progress', permission_classes=[AdminPermission])
    def get_progress(self, request):
        '''
        获取各区房屋使用数据百分比
        :param request: 请求对象
        :return: 返回包含各区房屋使用情况百分比的JSON数据响应对象
        '''
        # 获取各区房屋使用情况并格式化
        house_data = {
            item['area_code']: item['num'] for item in self.get_queryset().values('area_code').annotate(num=Count('*'))
        }
        # 获取全部房屋使用记录
        house_data['all'] = self.get_queryset().count()
        data = {
            'code': 0,
            'list': house_data
        }
        return Response(data)

    @action(methods=['get'], detail=False, url_path='data', permission_classes=[AdminPermission])
    def get_data(self, request):
        '''
        获取各区房屋使用情况
        :param request: 请求对象
        :return: 包含各区房屋使用情况的JSON数据响应对象
        '''
        # 获取各区房屋使用数目
        house_list = self.get_queryset().extra(select={'name': 'area_code'}).values('name').annotate(value=Count('*'))
        data = {
            'code': 0,
            'list': house_list
        }
        return Response(data)


def login_success(request, user, login_type):
    '''
    用户登录成功后生成token并存储到redis中
    :param login_type: 登录方式
    :param request:请求对象
    :param user:用户对象
    :return:响应数据及响应状态码
    '''
    data = {'code': 0}
    # 用户登录
    login(request, user)
    # 初始化状态码
    status_code = status.HTTP_200_OK
    # 获取请求认证头
    key = get_authorization_header(request).split()
    # 获取当前用户的username和name组成key并序列化
    user_key = ujson.dumps({'username': request.user.username, 'name': request.user.name}, ensure_ascii=False)
    # 如果login_ranking不存在则进行初始化
    if not REDIS_CLIENT.exists('login_ranking'):
        REDIS_CLIENT.zadd('login_ranking', {0: 0})
        REDIS_CLIENT.expireat('login_ranking', 60 * 60 * 24)
    # 如果user不存在于有序集合中则将它加入有序集合并设置分数为1表示登录了一次
    if REDIS_CLIENT.zscore('login_ranking', user_key) is None:
        REDIS_CLIENT.zadd('login_ranking', {user_key: 1})
        # 如果有序集合数大于10则删除分数低于第10名全部元素
        if REDIS_CLIENT.zcard('login_ranking') > 10:
            # 删除前面0到-11的元素，有序集合默认按分数低到高排序，-1分数最高
            REDIS_CLIENT.zremrangbyrank('login_ranking', 0, -11)
    else:
        # 如果已存在则将分数+1
        REDIS_CLIENT.zincrby('login_ranking', 1, user_key)
    # 登录方式+1
    if not cache.get(login_type, 0):
        cache.set(login_type, 0, 60*60*24)
    cache.incr(login_type)
    # 存入数据后设置过期时间
    if REDIS_CLIENT.bitcount(login_type) == 1:
        REDIS_CLIENT.expireat(login_type, 60 * 60 * 24)
    # 如果token还在有效期则不生成新token
    token = key[1] if key and cache.ttl(key) > 0 else binascii.hexlify(os.urandom(20)).decode()
    data['token'] = token
    # 封装用户信息
    user_info = {
        'id': request.user.pk,
        'username': request.user.username,
        'name': request.user.name,
        'group': request.user.group,
        'avatar': request.user.avatar
    }
    # 将用户信息序列化后存入redis中有效期7天
    cache.set_many({token: ujson.dumps(user_info)}, 60 * 60 * 24 * 7)
    return data, status_code


class UserViewSet(ModelViewSet):
    '''
    用户账号操作模型视图集
    '''
    authentication_classes = []
    queryset = User.objects.all()
    permission_classes = []
    serializer_class = UserModelSerializers

    @action(methods=['post'], detail=False, url_path='exist')
    def is_exists(self, request):
        '''
        判断用户所填的账号、手机号、车位、房屋是否存在
        :param request: 请求对象
        :return: 判断结果
        '''
        # 获取验证信息
        username = request.data.get('username')
        phone = request.data.get('phone')
        address = request.data.get('address')
        parking = request.data.get('parking')
        # 响应对象
        data = None
        try:
            # 验证手机号
            if phone:
                # 尝试根据手机号获取用户对象
                user = self.get_queryset().get(phone=phone)
                # 如果可以获取到用户
                if user:
                    # 手机号持有人和当前用户不一致则说明已被他人使用，否则可认为号码不存在
                    data = {'code': 0} if user.username != username else {'code': 1}
            # 仅验证用户名
            elif username:
                # 尝试根据用户名获取用户对象
                self.get_queryset().get(username=username)
                data = {'code': 0}
            # 验证住址
            elif address:
                # 尝试获取房屋对象
                house = House.objects.get(house_id=address)
                # 如果成功获取到房屋对象
                if house:
                    # 房屋持有人和当前用户不一致则说明已被他人使用，否则可认为房屋不存在即未被使用
                    data = {'code': 0} if house.username != username else {'code': 1}
            # 验证车位
            elif parking:
                # 尝试获取车位对象
                parking = Parking.objects.get(parking_lot_id=parking)
                # 如果成功获取到车位对象
                if parking:
                    # 车位持有人和当前用户不一致则说明已被他人使用，否则可认为车位不存在即未被使用
                    data = {'code': 0} if parking.username != username else {'code': 1}
        except:
            # 如果出现异常则说明验证数据不存在
            data = {'code': 1}
        return Response(data)

    @action(methods=['post'], detail=False, url_path='code')
    def get_code(self, request):
        '''
        发送验证码
        :param request:请求对象
        :return: 包含发送成功提示信息的JSON数据响应对象
        '''
        # 随机生成登录验证码
        login_code = random.randint(100000, 999999)
        # 获取短信对象
        sms = SendSms()
        # 根据用户号码发送短信
        sms.main(request.data.get('phone'), str(login_code))
        # redis保存短信验证码60s
        cache.set('code', str(login_code), 60)
        return Response({'code': 0})

    @action(methods=['post'], detail=False, url_path='login')
    def login(self, request):
        '''
        用户登录
        :param request: 请求对象
        :return: 包含登录结果的JSON数据响应对象
        '''
        # 登录方式，0为账号密码登录，1为手机号验证码登录
        login_type = request.data.get('type')
        status_code = status.HTTP_401_UNAUTHORIZED
        # 如果是手机号验证码登录
        if login_type:
            # 获取登录对象信息
            phone = request.data.get('phone')
            code = request.data.get('code')
            try:
                # 获取手机号用户对象
                user = self.get_queryset().get(phone=phone)
                # 如果验证码正确则执行用户登录
                if cache.get('code') == code:
                    # 执行用户登录
                    data, status_code = login_success(request, user, 'phone')
                else:
                    # 验证码不正确则不予以登录
                    data = {'code': 1}
            except User.DoesNotExist:
                # 手机号无效不予以登录
                data = {'code': 1}
        # 如果是账号密码登录
        else:
            # 获取用户账户名和密码
            username = request.data.get('username')
            password = request.data.get('password')
            # 登录信息验证
            user = authenticate(username=username, password=password)
            # 验证通过则登录系统
            if user is not None:
                # 执行用户登录
                data, status_code = login_success(request, user, 'id')
            else:
                # 如果登录信息验证不通过则不予以登录
                data = {'code': 1}
        return Response(data, status=status_code)

    @action(methods=['get'], detail=False, url_path='logout')
    def logout(self, request):
        '''
        用户登出
        :param request:请求对象
        :return: 响应对象
        '''
        # 登出当前账号
        logout(request)
        # 获取token
        token = request.META.get('HTTP_AUTHORIZATION').split()[1]
        # 从redis中删除用户token
        cache.delete(token)
        return Response({'code': 0}, status=status.HTTP_204_NO_CONTENT)

    @action(methods=['post'], detail=False, url_path='register')
    def register(self, request):
        '''
        用户注册
        :param request:请求对象
        :return: 包含注册结果的JSON数据响应对象
        '''
        # 数据校验
        serializer = self.get_serializer(data=request.data)
        # 如果校验通过
        if serializer.is_valid(raise_exception=True):
            # 写入数据
            serializer.save()
            # 社区总用户+1
            cache.get_or_set('all_user', 0, 60 * 60 * 24)
            cache.incr('all_user')
            return Response({'code': 0}, status=status.HTTP_201_CREATED)
        return Response({'code': 1}, status=status.HTTP_204_NO_CONTENT)


# 消息通知数据模型器类
class MessageModelViewSet(ModelViewSet):
    pagination_class = CommentsPagination
    queryset = Message.objects.all()
    serializer_class = MessageSerializers
    filterset_class = MessageFilter

    def create(self, request, *args, **kwargs):
        # 如果请求内容有id字段则说明是反馈回复
        if request.data.get('id'):
            # 将反馈任务状态从未处理调整为已处理
            instance = Evaluate.objects.filter(id=request.data.pop('id'))
            instance.update(status=1)
            # 获取用户服务对象和用户缴费对象
            try:
                UserService.objects.filter(order_id=instance.first().record_id, name=instance.first().name).update(
                    status=3)
            except:
                UserPayment.objects.filter(order_id=instance.first().record_id, name=instance.first().name).update(
                    status=3)
        # 将信息与当前用户绑定
        request.data['username'] = request.user.pk
        return super().create(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        # 返回接收人id等于当前用户的信息
        return Response({
            'code': 0,
            'list': self.get_serializer(self.get_queryset().filter(recipient_id=request.user.username), many=True,
                                        fields=('id', 'recipient_name', 'create_time', 'content')).data
        })


def export_excel(request):
    '''
    导出excel文件
    :param request:请求对象
    :return: excel文件数据流对象
    '''
    row = 1
    # 获取需要的数据类型
    data_type = int(request.GET.get('type'))
    # 获取token
    token = request.META.get('HTTP_AUTHORIZATION').split()[1]
    user_id = ujson.loads(cache.get(token)).get('id')
    # 设定编码类型为UTF-8
    wb = xlwt.Workbook(encoding='utf-8')
    # excel添加类别
    sheet = wb.add_sheet(u'表格')
    # 获取需要的数据对象
    obj_list = [UserService, UserPayment, User, Publicity, RepairsApply, Evaluate, Comments]
    obj = obj_list[data_type]
    # 配置响应头
    res = HttpResponse(content_type="application/vnd.ms-excel")
    res.setdefault("Access-Control-Expose-Headers", "Content-Disposition")
    res["Content-Disposition"] = f'attachment;filename={obj.__name__}.xls'
    # 获取数据值列表
    data_list = obj.objects.filter(username__id=user_id).values() if data_type < 2 else obj.objects.values()
    # 获取所有字段名列表
    fields = [field for field in data_list[0].keys()]
    # 将字段名写入文档第一行
    for i in range(len(fields)):
        sheet.write(0, i, fields[i])
    # 将数据按行写入文档
    for items in data_list:
        row_data = list(items.values())
        for i in range(len(row_data)):
            sheet.write(row, i, row_data[i])
        row = row + 1
    # 创建字节流对象
    output = BytesIO()
    # 将字节流对象保存
    wb.save(output)
    # 移动偏移指针
    output.seek(0)
    # 将字节流数据写入响应对象
    res.write(output.getvalue())
    # 关闭字节流对象
    output.close()
    return res


def data_show(request):
    '''
    用于获取系统监控数据
    :param request: 请求对象
    :return: 包含系统监控信息的JSON数据响应对象
    '''
    data = None
    # 获取data_key用于区分返回数据
    data_key = request.GET.get('data_key')
    match data_key:
        # 获取社区基本数据
        case '0':
            # 如果缓存数据不完整则重新获取缓存
            if len(cache.get_many(['all_user', 'house', 'resident', 'parking'])) < 4:
                # 每30天更新一次缓存
                cache.set_many({
                    # 获取总人数
                    'all_user': User.objects.count(),
                    # 获取剩余房屋数
                    'house': 405 - House.objects.all().count(),
                    # 获取已使用房屋数
                    'resident': House.objects.all().count(),
                    # 获取剩余车位数
                    'parking': 405 - Parking.objects.all().count()
                }, 60 * 60 * 24 * 30)
            data = {
                'code': 0,
                'data': cache.get_many(['all_user', 'house', 'resident', 'lessee', 'parking'])
            }
        # 获取redis调用数据
        case '1':
            cache.incr('redis')
            data = {'code': 0, 'total': cache.get('redis')}
        # 获取mysql调用数据
        case '2':
            cache.incr('mysql')
            data = {'code': 0, 'total': cache.get('mysql')}
    return JsonResponse(data)


def get_record(request):
    """
    获取用户的7天内的记录用于活动报名、用户缴费、房屋使用、车位使用信息展示
    :param request:请求对象
    :return:需要的用户报名记录的json数据
    """
    res = {
        'code': 0,
    }
    data_key = request.GET.get('data_key')
    match data_key:
        case '1':
            # 获取7天内的用户活动申请记录
            res['data'] = {
                'list': list(ActivityApply.objects.filter(create_time__gte=datetime.datetime.utcnow() -
                                                                           datetime.timedelta(weeks=1)).values(
                    'username__name', 'publicity__title', 'status'))
            }
        case '2':
            # 获取7天内的用户缴费申请记录
            res['data'] = {
                'list': list(Payment.objects.filter(create_time__gte=datetime.datetime.utcnow() -
                                                                     datetime.timedelta(weeks=1)).values(
                    'username__name', 'name', 'status'))
            }
        case '3':
            # 获取7天内的用户车位购买申请记录
            res['data'] = {
                'list': list(Parking.objects.filter(create_time__gte=datetime.datetime.utcnow() -
                                                                     datetime.timedelta(weeks=1)).values(
                    'username__name', 'parking_lot_id', 'status'))
            }
        case '4':
            # 获取7天内的用户房屋购买申请记录
            res['data'] = {
                'list': list(House.objects.filter(create_time__gte=datetime.datetime.utcnow() -
                                                                   datetime.timedelta(weeks=1)).values(
                    'username__name', 'house_id', 'status'))
            }
        case '5':
            # 获取7天内的用户维修申请记录
            res['data'] = {
                'list': list(RepairsApply.objects.filter(create_time__gte=datetime.datetime.utcnow() -
                                                                          datetime.timedelta(weeks=1)).values(
                    'username__name', 'name', 'status'))
            }
    return JsonResponse(res, safe=False)
