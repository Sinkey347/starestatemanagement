"""StarEstateManagement URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.views.generic.base import TemplateView
from django.urls import include, path, re_path
from django.views.static import serve
from drf_yasg2 import openapi
from drf_yasg2.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    # 配置接口文档信息
    openapi.Info(
        title='Sinkey API',
        default_version='v1',
        description="Welcome to Sinkey's world"
    ),
    # 公开访问
    public=True,
    # 管理员都拥有访问权限
    permission_classes=(permissions.AllowAny,)
)

urlpatterns = [
    re_path(r'^doc(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('doc/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-swagger-redoc'),
    path('api/', include('star_api.urls')),
    path('admin/', admin.site.urls),
    re_path(r'media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    path('', TemplateView.as_view(template_name='index.html')),
]
