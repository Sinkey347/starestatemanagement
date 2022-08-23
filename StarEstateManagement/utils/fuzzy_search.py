import django_filters
from django.http import request
from django_filters.rest_framework import FilterSet
from star_db.models import User, ActivityApply, RepairsApply, UserService, Evaluate, Comments, Payment, Parking, House, \
    Message, UserPayment


class UserFilter(FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    group = django_filters.CharFilter(field_name='group', lookup_expr='icontains')
    status = django_filters.CharFilter(field_name='status', lookup_expr='icontains')
    create_time = django_filters.CharFilter(field_name='create_time', lookup_expr='icontains')
    update_time = django_filters.CharFilter(field_name='update_time', lookup_expr='icontains')

    class Meta:
        models = User
        filter_fields = ['name', 'group', 'status', 'create_time', 'update_time']


class PublicityFilter(FilterSet):
    user_name = django_filters.CharFilter(field_name='username__name', lookup_expr='icontains')
    type = django_filters.CharFilter(field_name='type', lookup_expr='icontains')
    status = django_filters.CharFilter(field_name='status', lookup_expr='icontains')
    create_time = django_filters.CharFilter(field_name='create_time', lookup_expr='icontains')

    class Meta:
        models = User
        filter_fields = ['user_name', 'type', 'status', 'create_time']


class ActivityApplyFilter(FilterSet):
    a_name = django_filters.CharFilter(field_name='publicity__title', lookup_expr='icontains')

    class Meta:
        models = ActivityApply
        filter_fields = ['a_name']


class RepairsFilter(FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    type = django_filters.CharFilter(field_name='type', lookup_expr='icontains')
    status = django_filters.CharFilter(field_name='status', lookup_expr='icontains')
    create_time = django_filters.CharFilter(field_name='create_time', lookup_expr='icontains')

    class Meta:
        models = RepairsApply
        filter_fields = ['name', 'type', 'status', 'create_time']


class ServiceFilter(FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    type = django_filters.CharFilter(field_name='type', lookup_expr='icontains')
    status = django_filters.CharFilter(field_name='status', lookup_expr='icontains')
    create_time = django_filters.CharFilter(field_name='create_time', lookup_expr='icontains')

    class Meta:
        models = UserService
        filter_fields = ['name', 'type', 'status', 'create_time']





class EvaluateFilter(FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    type = django_filters.CharFilter(field_name='type', lookup_expr='icontains')
    status = django_filters.CharFilter(field_name='status', lookup_expr='icontains')
    create_time = django_filters.CharFilter(field_name='create_time', lookup_expr='icontains')

    class Meta:
        models = Evaluate
        filter_fields = ['u_id', 'name', 'type', 'status', 'create_time']


class CommentsFilter(FilterSet):
    type = django_filters.CharFilter(field_name='type', lookup_expr='icontains')
    page_id = django_filters.CharFilter(field_name='page_id', lookup_expr='icontains')
    user_name = django_filters.CharFilter(field_name='username__name', lookup_expr='icontains')
    status = django_filters.CharFilter(field_name='status', lookup_expr='icontains')
    create_time = django_filters.CharFilter(field_name='create_time', lookup_expr='icontains')

    class Meta:
        models = Comments
        filter_fields = ['type', 'page_id', 'father_id', 'status', 'create_time', 'user_name']


class UserPaymentFilter(FilterSet):
    user_id = django_filters.CharFilter(field_name='username__id')
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    status = django_filters.CharFilter(field_name='status', lookup_expr='icontains')
    create_time = django_filters.CharFilter(field_name='create_time', lookup_expr='icontains')

    class Meta:
        models = UserPayment
        filter_fields = ['user_id', 'name', 'status', 'create_time']


class PaymentFilter(FilterSet):
    id = django_filters.CharFilter(field_name='id')

    class Meta:
        models = Payment
        filter_fields = ['id']


class ParkingFilter(FilterSet):
    id = django_filters.CharFilter(field_name='payment__id')

    class Meta:
        models = Parking
        filter_fields = ['id']


class HouseFilter(FilterSet):
    id = django_filters.CharFilter(field_name='payment__id')

    class Meta:
        models = House
        filter_fields = ['id']


class MessageFilter(FilterSet):
    user_id = django_filters.CharFilter(field_name='username__username')

    class Meta:
        models = Message
        filter_fields = ['user_id']
