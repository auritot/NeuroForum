from typing import Dict, Any
import re
import html

def response(status, message, data=None):
    response_data: Dict[str, Any] = {"status": status, "message": message}

    if data is not None:
        response_data["data"] = data

    return response_data

def get_pagination_data(current_page: int, per_page: int, total_count: int):
    total_pages = (total_count + per_page - 1) // per_page
    start_index = (current_page - 1) * per_page
    page_range = range(1, total_pages + 1)
    previous_page = current_page - 1 if current_page > 1 else None
    next_page = current_page + 1 if current_page < total_pages else None

    return {
        "start_index": start_index,
        "total_pages": total_pages,
        "page_range": page_range,
        "current_page": current_page,
        "previous_page": previous_page,
        "next_page": next_page,
    }

def sanitize_input(data: str) -> str:
    """ Cleans input by trimming and escaping HTML. """
    data = data.strip()               # Remove leading/trailing whitespace
    data = html.escape(data)          # Escape HTML special characters
    return data

def validate_email(data: str) -> bool:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w{2,}$"
    return re.match(pattern, data) is not None
