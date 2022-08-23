from rest_framework.pagination import PageNumberPagination


class CommentsPagination(PageNumberPagination):
    # 每页的数据量
    page_size = 1000
    # 每页数据量参数
    page_size_query_param = 'page_size'  #
    # 分页参数
    page_query_param = 'page'
    # 最多能显示多少页
    max_page_size = 100
