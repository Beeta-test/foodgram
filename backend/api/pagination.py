from rest_framework.pagination import LimitOffsetPagination

from backend.consts import PAGE_SIZE


class LimitPageNumberPagination(LimitOffsetPagination):
    page_size_query_param = 'limit'
    page_size = PAGE_SIZE
