from django.contrib.auth import get_user_model
from django.db import models
from django.contrib.auth.models import AbstractUser
from utils.constant import *


# Create your models here.


class User(AbstractUser):
    """
    用户信息模型类
    """
    # 删除字段
    first_name = None
    last_name = None
    # 添加字段
    name = models.CharField(max_length=5, null=True, verbose_name="姓名")
    avatar = models.CharField(max_length=100, default=AVATAR_DEFAULT_IMAGE, verbose_name='头像')
    phone = models.CharField(max_length=13, db_index=True, unique=True, null=True, verbose_name='手机号')
    sex = models.SmallIntegerField(default=1, verbose_name='性别')  # 1男、0女
    group = models.SmallIntegerField(default=0, verbose_name="用户组")  # 0普通用户、1维修师傅、2管理员
    id_num = models.CharField(max_length=20, null=True, verbose_name='证件号')
    message = models.CharField(max_length=200, null=True, verbose_name='备注')
    check_in = models.DateTimeField(max_length=19, null=True, verbose_name='入住时间')
    status = models.SmallIntegerField(default=2, verbose_name='账号状态')  # 0异常、1监控、2正常
    info_complete = models.BooleanField(default=False, verbose_name='信息完整')
    task_id = models.SmallIntegerField(default=0, null=True, verbose_name='已承接任务id')
    # 采用二进制表示，水费、电费、燃气费、物业费从左至右各占1位，1111=7,表示本月费用全部交齐,0000=0表示本月未缴费
    payment_id = models.SmallIntegerField(default=0, null=True, verbose_name='已缴费项目id')
    login = models.SmallIntegerField(default=0, verbose_name='今日登录次数')
    create_time = models.DateTimeField(max_length=19, auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(max_length=19, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'user'


class Publicity(models.Model):
    """
    通知管理模型类
    """
    username = models.ForeignKey(User, on_delete=models.CASCADE, related_name='u_publicity',
                                 db_index=True, db_constraint=False)
    type = models.SmallIntegerField(default=0, verbose_name='通知类型')  # 0社区公告、1活动发布、2收费通知
    title = models.CharField(max_length=10, verbose_name='通知标题')
    content = models.CharField(max_length=200, null=True, verbose_name='通知内容')
    img = models.CharField(max_length=100, verbose_name='通知图片')
    address = models.CharField(max_length=30, null=True, verbose_name='活动地址')
    money = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name='收费金额')
    start = models.DateTimeField(max_length=19, null=True, verbose_name='开始时间')
    end = models.DateTimeField(max_length=19, null=True, verbose_name='截止时间')
    join = models.SmallIntegerField(default=0, verbose_name='缴费人数')
    need = models.SmallIntegerField(default=0, verbose_name='需要人数')
    status = models.BooleanField(default=0, verbose_name='发布状态')  # 0公示中、1已过期
    create_time = models.DateTimeField(max_length=19, auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(max_length=19, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'publicity'


class ActivityApply(models.Model):
    """
    活动管理模型类
    """
    publicity = models.ForeignKey(Publicity, on_delete=models.CASCADE, related_name='p_activity_apply',
                                  db_constraint=False)
    username = models.ForeignKey(User, on_delete=models.CASCADE, related_name='u_activity_apply',
                                 db_constraint=False)
    # registration = models.SmallIntegerField(default=0, verbose_name='活动报名情况')
    status = models.SmallIntegerField(default=0, verbose_name='申请状态')  # 0待处理、1已受理、2维修中、3已完成、4已同意、5已拒绝、6反馈中、7已评价
    create_time = models.DateTimeField(max_length=19, auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(max_length=19, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'activity_apply'
        # 唯一联合索引
        unique_together = (
            ('username', 'publicity'),
        )


class RepairsApply(models.Model):
    """
    维修申请管理
    """
    # wx_id = models.CharField(max_length=10, primary_key=True, verbose_name='维修申请id')
    name = models.CharField(max_length=100, null=True, verbose_name='维修任务')
    type = models.CharField(default='P3', max_length=3, verbose_name='维修类型')  # C社区报修 P个人报修，0供水、1供电、2燃气，3其他
    status = models.SmallIntegerField(default=0, verbose_name='维修状态')  # # 0待处理、1已受理、2维修中、3已完成、4已同意、5已拒绝、6反馈中、7已评价
    username = models.ForeignKey(User, on_delete=models.CASCADE, related_name='u_repairs',
                                 db_index=True, db_constraint=False)
    worker_name = models.CharField(max_length=4, null=True, verbose_name='维修师傅')
    worker_id = models.IntegerField(null=True, verbose_name='师傅工号')
    create_time = models.DateTimeField(max_length=19, auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(max_length=19, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'repairs_apply'


class UserService(models.Model):
    """
    用户服务管理模型类
    """
    username = models.ForeignKey(User, on_delete=models.CASCADE, related_name='u_user_service',
                                 db_index=True, db_constraint=False)
    order_id = models.SmallIntegerField(verbose_name='服务单号')
    name = models.CharField(max_length=100, verbose_name='服务任务名')
    type = models.CharField(default='', max_length=3, verbose_name='服务类型')  # A社区活动 C公共报修 P个人报修，0供水、1供电、2燃气，3其他
    status = models.SmallIntegerField(default=0, verbose_name='服务状态')  # 0待处理、1已受理、2维修中、3已完成、4已同意、5已拒绝、6反馈中、7已评价
    score = models.FloatField(null=True, verbose_name='评价分数')
    create_time = models.DateTimeField(max_length=19, auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(max_length=19, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'user_service'


class Evaluate(models.Model):
    """
    评价反馈模型类
    """
    username = models.ForeignKey(User, on_delete=models.CASCADE, related_name='u_evaluate',
                                 db_index=True, db_constraint=False)
    name = models.CharField(max_length=30, null=True, verbose_name='评价任务')
    record_id = models.CharField(max_length=10, verbose_name='任务记录id')
    type = models.BooleanField(default=0, verbose_name='评价类型')  # 0评价 1反馈
    weekday = models.SmallIntegerField(default=0, verbose_name='星期数')
    score = models.FloatField(default=0.0, null=True, verbose_name='评价分数')
    content = models.CharField(max_length=100, null=True, verbose_name='反馈内容')
    status = models.BooleanField(default=0, verbose_name='任务状态')  # 0未受理、1已完成
    create_time = models.DateTimeField(max_length=19, auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(max_length=19, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'evaluate'


class Comments(models.Model):
    """
    留言评论管理模型类
    """
    username = models.ForeignKey(User, on_delete=models.CASCADE,
                                 related_name='u_comments', db_index=True, db_constraint=False)
    comment = models.CharField(max_length=300, null=True, verbose_name='提交评论内容')
    replay_name = models.CharField(max_length=5, null=True, verbose_name='回复人姓名')
    type = models.BooleanField(default=0, verbose_name='评论类型')  # 0留言、1评论
    page_name = models.CharField(max_length=30, default='留言板', verbose_name='来源页面名字')
    page_id = models.SmallIntegerField(default=0, verbose_name='来源页面id')
    status = models.BooleanField(default=1, verbose_name='发布状态')  # 0屏蔽、1正常
    father_id = models.IntegerField(default=0, null=True, verbose_name='父评论id')
    good = models.SmallIntegerField(default=0, verbose_name='评论数')
    show = models.BooleanField(default=1, verbose_name='是否显示')
    create_time = models.DateTimeField(max_length=19, auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(max_length=19, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'comments'


class Payment(models.Model):
    """
    缴费管理模型类
    """
    username = models.ForeignKey(User, on_delete=models.CASCADE, related_name='u_payment',
                                 db_index=True, db_constraint=False)
    name = models.CharField(max_length=20, verbose_name='费用名字')
    status = models.SmallIntegerField(default=0, verbose_name='收费状态')  # 0待处理、1已受理、2维修中、3已完成、4已同意、5已拒绝、6反馈中、7已评价
    type = models.SmallIntegerField(default=0, verbose_name='收费类型')  # 0水费、1电费、2物业费、3、燃气费、4房屋保证金、5车位保证金
    money = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='收费金额')
    create_time = models.DateTimeField(max_length=19, auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(max_length=19, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'payment'


class UserPayment(models.Model):
    """
    用户缴费情况模型类
    """
    username = models.ForeignKey(User, on_delete=models.CASCADE,
                                 related_name='u_user_payment', db_index=True, db_constraint=False)
    money = models.DecimalField(max_digits=10, default=0.0, decimal_places=2, verbose_name='支付价格')
    name = models.CharField(max_length=10, default='', verbose_name='款项名')
    type = models.SmallIntegerField(default=0, verbose_name='费用类型')  # 0水费、1电费、2物业费、3、燃气费、4房屋保证金、5车位保证金
    order_id = models.SmallIntegerField(default=0, verbose_name='订单号')
    status = models.SmallIntegerField(default=0, verbose_name='缴费状态')  # 0待处理、1已受理、2维修中、3已完成、4已同意、5已拒绝、6反馈中、7已评价
    score = models.FloatField(null=True, verbose_name='评价分数')
    create_time = models.DateTimeField(max_length=19, auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(max_length=19, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'user_payment'


class Parking(models.Model):
    """
    车位管理模型类
    """
    username = models.OneToOneField(User, on_delete=models.CASCADE, unique=True,
                                    related_name='u_parking', db_constraint=False)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='p_parking',
                                   verbose_name='付款单号', db_index=True, db_constraint=False)
    parking_lot_id = models.CharField(max_length=5, unique=True, verbose_name='车位号')
    area_code = models.CharField(max_length=1, default='A', db_index=True, verbose_name='区号')
    status = models.SmallIntegerField(default=0, verbose_name='车位状态')  # 0待处理、1已受理、2维修中、3已完成、4已同意、5已拒绝、6反馈中、7已评价
    create_time = models.DateTimeField(max_length=19, auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(max_length=19, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'parking'
        index_together = (
            ('username', 'parking_lot_id')
        )


class House(models.Model):
    """
    房屋管理模型类
    """
    username = models.OneToOneField(User, on_delete=models.CASCADE, unique=True,
                                    related_name='u_house', db_constraint=False)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='p_house',
                                   db_index=True, verbose_name='付款单号', db_constraint=False)
    house_id = models.CharField(max_length=5, unique=True, verbose_name='房屋号')
    area_code = models.CharField(max_length=1, db_index=True, default='A', verbose_name='区号')
    status = models.SmallIntegerField(default=0, verbose_name='房屋状态')  # 0待处理、1已受理、2维修中、3已完成、4已同意、5已拒绝、6反馈中、7已评价
    create_time = models.DateTimeField(max_length=19, auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(max_length=19, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'house'
        index_together = (
            ('username', 'house_id')
        )


class Message(models.Model):
    """
    用户消息管理模型类
    """
    username = models.ForeignKey(User, on_delete=models.CASCADE, related_name='u_message',
                                 db_constraint=False, db_index=True, verbose_name='发送者')
    recipient_id = models.CharField(default='', max_length=10, verbose_name='接收人账号')
    recipient_name = models.CharField(default='', max_length=5, verbose_name='接收人姓名')
    content = models.CharField(default='', max_length=100, verbose_name='消息内容')
    create_time = models.DateTimeField(max_length=19, auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(max_length=19, auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'Message'
