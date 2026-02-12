"""
Standardized API response utilities for runit-server.
"""
from typing import Any, Dict, Optional, Union
from fastapi.responses import JSONResponse


class APIResponse:
    """Standardized API response builder."""
    
    @staticmethod
    def success(
        data: Optional[Any] = None,
        message: Optional[str] = None,
        status_code: int = 200,
        **kwargs
    ) -> JSONResponse:
        """Build a success response."""
        response = {"status": "success"}
        
        if message:
            response["message"] = message
        if data is not None:
            response["data"] = data
        
        response.update(kwargs)
        return JSONResponse(response, status_code=status_code)
    
    @staticmethod
    def error(
        message: str = "An error occurred",
        error_code: Optional[str] = None,
        status_code: int = 400,
        details: Optional[Dict] = None,
        **kwargs
    ) -> JSONResponse:
        """Build an error response."""
        response = {
            "status": "error",
            "message": message
        }
        
        if error_code:
            response["error_code"] = error_code
        if details:
            response["details"] = details
        
        response.update(kwargs)
        return JSONResponse(response, status_code=status_code)
    
    @staticmethod
    def created(
        data: Optional[Any] = None,
        message: str = "Resource created successfully",
        **kwargs
    ) -> JSONResponse:
        """Build a 201 Created response."""
        return APIResponse.success(data, message, 201, **kwargs)
    
    @staticmethod
    def not_found(
        resource: str = "Resource",
        **kwargs
    ) -> JSONResponse:
        """Build a 404 Not Found response."""
        return APIResponse.error(
            message=f"{resource} not found",
            error_code="NOT_FOUND",
            status_code=404,
            **kwargs
        )
    
    @staticmethod
    def unauthorized(
        message: str = "Unauthorized",
        **kwargs
    ) -> JSONResponse:
        """Build a 401 Unauthorized response."""
        return APIResponse.error(
            message=message,
            error_code="UNAUTHORIZED",
            status_code=401,
            **kwargs
        )
    
    @staticmethod
    def forbidden(
        message: str = "Forbidden",
        **kwargs
    ) -> JSONResponse:
        """Build a 403 Forbidden response."""
        return APIResponse.error(
            message=message,
            error_code="FORBIDDEN",
            status_code=403,
            **kwargs
        )
    
    @staticmethod
    def validation_error(
        errors: Dict,
        message: str = "Validation failed",
        **kwargs
    ) -> JSONResponse:
        """Build a 422 Validation Error response."""
        return APIResponse.error(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=errors,
            **kwargs
        )
    
    @staticmethod
    def rate_limited(
        retry_after: int,
        **kwargs
    ) -> JSONResponse:
        """Build a 429 Rate Limited response."""
        response = JSONResponse(
            {
                "status": "error",
                "message": "Too many requests",
                "error_code": "RATE_LIMITED",
                "retry_after": retry_after
            },
            status_code=429,
            headers={"Retry-After": str(retry_after)}
        )
        return response


class ErrorCodes:
    """Standard error codes for the API."""
    
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
