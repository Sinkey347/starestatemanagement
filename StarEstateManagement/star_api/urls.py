from . import views
from django.urls import path
from rest_framework.routers import DefaultRouter


router = DefaultRouter()  # 实例化路由集对象
router.register("users", views.UserModelViewSet)
router.register("activity-apply", views.ActivityApplyModelViewSet)
router.register("publicity", views.PublicityModelViewSet)
router.register('repairs', views.RepairsApplyModelViewSet)
router.register('services', views.UserServiceModelViewSet)
router.register('evaluate', views.EvaluateModelViewSet)
router.register('comments', views.CommentsModelViewSet)
router.register('money', views.PaymentModelViewSet)
router.register('payments', views.UserPaymentsModelViewSet)
router.register('parking', views.ParkingModelViewSet)
router.register('house', views.HouseModelViewSet)
router.register('messages', views.MessageModelViewSet)
router.register('account', views.UserViewSet)

urlpatterns = [
                  path('download/', views.export_excel),
                  path('data/', views.data_show),
                  path('record/', views.get_record),

              ] + router.urls
