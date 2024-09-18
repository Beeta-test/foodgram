from rest_framework.pagination import LimitOffsetPagination


class LimitPageNumberPagination(LimitOffsetPagination):
    page_size_query_param = 'limit'
    page_size = 6
