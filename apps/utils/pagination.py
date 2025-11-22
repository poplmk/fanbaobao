from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """标准分页器"""

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'code': 200,
            'message': 'success',
            'data': {
                'count': self.page.paginator.count,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'results': data,
                'page_size': self.get_page_size(self.request),
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
            }
        })


class LargeResultsSetPagination(StandardResultsSetPagination):
    """大容量分页器"""
    page_size = 100
    max_page_size = 1000


class SmallResultsSetPagination(StandardResultsSetPagination):
    """小容量分页器"""
    page_size = 10
    max_page_size = 50