from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from utils.constant import REDIS_CLIENT
from utils.custom_serializer import DynamicFieldsModelSerializer
from star_db.models import User, ActivityApply, Publicity, RepairsApply, UserService, Evaluate, Comments, \
    Payment, UserPayment, Parking, House, Message


class UserModelSerializers(DynamicFieldsModelSerializer):
    """ 用户信息序列化器 """
    address = serializers.SerializerMethodField(label='住址')
    parking = serializers.SerializerMethodField(label='车位')

    class Meta:
        model = User  # 获取User的字段数据格式
        fields = ['id', 'username', 'status', 'avatar', 'create_time', "name",
                  'group', 'update_time', 'sex', 'id_num', 'phone', 'message',
                  'address', 'parking', 'check_in', 'password', 'info_complete']
        extra_kwargs = {
            'password': {
                'write_only': True
            },
            'id': {
                'read_only': True
            }
        }

    # 3、数据操作
    def create(self, validated_data):
        """
        创建用户信息
        :param validated_data: 校验通过的数据
        :return: 校验数据
        """
        User.objects.create_user(**validated_data)
        return validated_data

    def update(self, instance, validated_data):
        """
        更新用户信息
        :param instance: 当前对象实例
        :param validated_data: 校验通过的数据
        :return:
        """
        # 如果包含密码则对密码单独加密
        if validated_data.get('password'):
            validated_data['password'] = make_password(validated_data.get('password'))
        return super().update(instance, validated_data)

    # 自定义方法字段
    def get_address(self, obj):
        if isinstance(obj, User) or obj.get('id'):
            user_house = House.objects.filter(username_id=obj.id).first()
            return user_house.house_id if user_house else None
        return None

    def get_parking(self, obj):
        if isinstance(obj, User) or obj.get('id'):
            user_parking = Parking.objects.filter(username_id=obj.id).first()
            return user_parking.parking_lot_id if user_parking else None
        return None


class ActivityApplySerializers(DynamicFieldsModelSerializer):
    """活动申请序列化器类"""
    p_join = serializers.CharField(source='publicity.join', read_only=True)
    p_need = serializers.CharField(source='publicity.need', read_only=True)
    p_name = serializers.CharField(source='publicity.title', read_only=True)
    user_id = serializers.CharField(source='username.username', read_only=True)
    user_name = serializers.CharField(source='username.name', read_only=True)

    class Meta:
        model = ActivityApply
        fields = [
            'id', 'p_name', 'p_join', 'p_need', 'user_name', 'user_id', 'status',
            'username', 'publicity', 'create_time', 'update_time'
        ]


class PublicitySerializers(DynamicFieldsModelSerializer):
    user_id = serializers.CharField(source='username.username', read_only=True)
    user_name = serializers.CharField(source='username.name', read_only=True)
    good = serializers.SerializerMethodField(label='文章点赞数')
    all = serializers.SerializerMethodField(label='社区总人数')

    class Meta:
        model = Publicity
        fields = ['id', 'user_id', 'user_name', 'type', 'title', 'content', 'status', 'create_time',
                  'img', 'title', 'good', 'join', 'need', 'money', 'all', 'username', 'start', 'end', 'address'
                  ]

    def get_good(self, obj):
        """
        根据通知id从redis中获取点赞数
        :param obj:当前实例对象
        :return:
        """
        return REDIS_CLIENT.bitcount(f'publicity{obj.id}')

    def get_all(self, obj):
        """
        从redis中获取社区总人数
        :return:
        """
        return cache.get_or_set('all_user', 0)


class RepairsApplySerializers(DynamicFieldsModelSerializer):
    user_id = serializers.CharField(source='username.username', read_only=True)
    user_name = serializers.CharField(source='username.name', read_only=True)

    class Meta:
        model = RepairsApply
        fields = [
            'id', 'name', 'type', 'user_name', 'user_id', 'status', 'username_id',
            'username', 'create_time', 'worker_name', 'worker_id', 'update_time'
        ]

    def update(self, instance, validated_data):
        # 如果传入了工人id和姓名则将工人与任务绑定
        if validated_data.get('worker_id'):
            queryset = User.objects.filter(id=validated_data.get('worker_id'))
            if queryset:
                queryset.update(task_id=validated_data.get('id'))
                validated_data['worker_name'] = queryset.first().name
        # 如果没有传入工人id则将说明任务已完成
        else:
            User.objects.filter(id=instance.worker_id).update(task_id=0)
        # 更新用户维修记录数据状态
        UserService.objects.filter(order_id=instance.id).update(status=validated_data.get('status'))
        return super().update(instance, validated_data)


class UserServiceSerializers(DynamicFieldsModelSerializer):
    user_id = serializers.CharField(source='username.username', read_only=True)
    user_name = serializers.CharField(source='username.name', read_only=True)

    class Meta:
        model = UserService
        fields = [
            'id', 'user_name', 'user_id', 'name', 'type',
            'status', 'score', 'order_id', 'create_time'
        ]


class EvaluateSerializers(serializers.ModelSerializer):
    user_name = serializers.CharField(source='username.name', read_only=True)
    user_id = serializers.CharField(source='username.username', read_only=True)

    class Meta:
        model = Evaluate
        fields = [
            'id', 'name', 'user_name', 'user_id', 'type', 'score', 'weekday',
            'username', 'content', 'status', 'create_time', 'record_id'
        ]


class CommentsSerializers(serializers.ModelSerializer):
    user_id = serializers.CharField(source='username.username')
    user_name = serializers.CharField(source='username.name')
    user_avatar = serializers.CharField(source='username.avatar')

    class Meta:
        model = Comments
        fields = [
            'id', 'user_name', 'user_id', 'user_avatar', 'replay_name', 'comment', 'type', 'page_name', 'page_id',
            'status', 'father_id', 'create_time', 'show', 'good'
        ]


class PaymentSerializers(serializers.ModelSerializer):
    user_name = serializers.CharField(source='username.name', read_only=True)
    user_id = serializers.CharField(source='username.username', read_only=True)
    user_phone = serializers.CharField(source='username.phone', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'username', 'user_name', 'user_id', 'name', 'type', 'status',
            'user_phone', 'money', 'create_time'
        ]


class UserPaymentSerializers(DynamicFieldsModelSerializer):
    user_id = serializers.CharField(source='username.username', read_only=True)
    user_name = serializers.CharField(source='username.name', read_only=True)

    class Meta:
        model = UserPayment
        fields = [
            'id', 'user_name', 'username', 'name', 'user_id', 'money', 'status',
            'type', 'order_id', 'create_time', 'score', 'update_time'
        ]


class ParkingSerializers(DynamicFieldsModelSerializer):
    user_name = serializers.CharField(source='username.name')
    user_id = serializers.CharField(source='username.username')
    id_num = serializers.CharField(source='username.id_num')
    phone = serializers.CharField(source='username.phone')
    order_id = serializers.CharField(source='payment.id')
    money = serializers.CharField(source='payment.money')

    class Meta:
        model = Parking
        fields = [
            'id', "username", 'user_name', 'user_id', 'id_num', 'phone', "parking_lot_id", "money",
            'payment', "create_time", "status", "order_id", "update_time"
        ]


class HouseSerializers(DynamicFieldsModelSerializer):
    user_name = serializers.CharField(source='username.name')
    user_id = serializers.CharField(source='username.username')
    id_num = serializers.CharField(source='username.id_num')
    phone = serializers.CharField(source='username.phone')
    order_id = serializers.CharField(source='payment.id')
    money = serializers.CharField(source='payment.money')

    class Meta:
        model = House
        fields = [
            'id', "username", 'user_name', 'user_id', 'id_num', 'phone', "house_id", "money",
            'payment', "create_time", "status", "order_id", "update_time"
        ]


class MessageSerializers(DynamicFieldsModelSerializer):
    user_id = serializers.CharField(source='username.username', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'username', 'recipient_id', 'recipient_name', 'content', 'create_time', 'user_id'
        ]
