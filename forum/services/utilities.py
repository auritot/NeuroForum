def response(status, message, data=None):
    response_data = {"status": status, "message": message}

    # If data is provided, add it to the response
    if data is not None:
        response_data["data"] = data

    return response_data
