def success_response(data=None, message="Success"):
    return {
        "success": True,
        "message": message,
        "data": data,
        "error": None,
    }


def error_response(message="Something went wrong", error=None):
    return {
        "success": False,
        "message": message,
        "data": None,
        "error": error,
    }
