response401 = {
    "description": "Unauthorized access",
    "content": {
        "application/json": {
            "example": {"detail": "Not authenticated"}
        }
    }
}

response403 = {
    "description": "User does not have permission to access this resource",
    "content": {
        "application/json": {
            "example": {"detail": "Access denied"}
        }
    }
}

response404 = {
    "description": "Resource not found",
    "content": {
        "application/json": {
            "example": {"detail": "Resource not found"}
        }
    }
}