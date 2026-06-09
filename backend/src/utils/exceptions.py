"""业务异常定义"""


class ServiceError(Exception):
    """业务逻辑异常，返回 400"""
    def __init__(self, detail: str):
        self.detail = detail
