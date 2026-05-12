from fastapi import HTTPException, status


class BusinessException(HTTPException):
    def __init__(self, code: int, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.biz_code = code
        super().__init__(status_code=status_code, detail=message)


class UnauthorizedException(BusinessException):
    def __init__(self, message: str = "未授权"):
        super().__init__(code=1002, message=message, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenException(BusinessException):
    def __init__(self, message: str = "无权访问"):
        super().__init__(code=1003, message=message, status_code=status.HTTP_403_FORBIDDEN)


class NotFoundException(BusinessException):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(code=1004, message=message, status_code=status.HTTP_404_NOT_FOUND)


class ConflictException(BusinessException):
    def __init__(self, message: str = "资源冲突"):
        super().__init__(code=1005, message=message, status_code=status.HTTP_409_CONFLICT)
