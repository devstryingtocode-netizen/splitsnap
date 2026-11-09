from app.schemas.errors import ErrorResponse

ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "The operation is invalid."},
    404: {"model": ErrorResponse, "description": "The resource was not found."},
    409: {"model": ErrorResponse, "description": "The operation conflicts with stored data."},
    422: {"model": ErrorResponse, "description": "Request validation failed."},
    500: {"model": ErrorResponse, "description": "An internal error occurred."},
    503: {
        "model": ErrorResponse,
        "description": "The development owner is not configured.",
    },
}
