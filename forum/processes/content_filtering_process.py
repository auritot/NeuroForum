import re
from typing import Tuple, List, Dict, Any
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from urllib.parse import urlencode

from ..services import session_utils, utilities
from ..services.db_services import ContentFiltering_service, log_service

# Constants for validation
FILTER_CONTENT_REGEX = r"^[\w '.@*-]+$"
FILTER_CONTENT_MAX_LENGTH = 255


def validate_filter_content(content: str) -> Tuple[bool, str]:
    """
    Validate filter content against our rules.
    
    Args:
        content (str): The content to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not content or not content.strip():
        return False, "Content cannot be empty."

    content = content.strip()

    if len(content) > FILTER_CONTENT_MAX_LENGTH:
        return False, f"Content is too long (max {FILTER_CONTENT_MAX_LENGTH} characters)."

    if not re.match(FILTER_CONTENT_REGEX, content):
        return False, "Invalid characters. Allowed: letters, numbers, underscores, spaces, hyphens, apostrophes, periods, '@', '*'."

    return True, ""


# MARK: Add Filtered Words
def process_add_filtered_words(request, context: Dict[str, Any]) -> Any:
    """
    Process adding one or more filtered words.
    
    Args:
        request: Django HTTP request object
        context: Dictionary containing pagination and search parameters
        
    Returns:
        Django redirect response
    """
    content_input = request.POST.get("filter_content", "").strip()
    
    # Extract form parameters for redirect
    page_from_form = request.POST.get("page", context.get('current_page', 1))
    search_from_form = request.POST.get("search", context.get('search_term', ''))
    sort_by_from_form = request.POST.get("sort_by", context.get('sort_by', 'FilterContent'))
    sort_order_from_form = request.POST.get("sort_order", context.get('sort_order', 'ASC'))

    # Split by newline, strip each line, and filter out empty lines
    words_to_add = [word.strip() for word in content_input.splitlines() if word.strip()]

    user_id = context.get('user_info', {}).get('UserID')
    if not words_to_add:
        messages.error(request, "No words provided to add. Please enter words in the textarea, one per line.")
        log_service.log_action(
            f"Admin user {user_id} failed to add filtered words: No words provided.",
            user_id, isSystem=False, isError=True)
    else:
        valid_words = []
        invalid_word_entries = []
        all_entries_valid = True

        for original_word_entry in words_to_add:
            is_valid, error_msg = validate_filter_content(original_word_entry)
            if is_valid:
                valid_words.append(original_word_entry)
            else:
                all_entries_valid = False
                if len(invalid_word_entries) < 5:  # Show a few examples
                    invalid_word_entries.append(original_word_entry)

        if not all_entries_valid:
            error_msg = f"One or more words are invalid. Allowed: letters, numbers, underscores, spaces, hyphens, apostrophes, periods, '@', '*'. Max {FILTER_CONTENT_MAX_LENGTH} characters per word."
            if invalid_word_entries:
                error_msg += f" Examples of invalid entries: '{', '.join(invalid_word_entries[:3])}'."
            messages.error(request, error_msg)
            log_service.log_action(
                f"Admin user {user_id} failed to add filtered words: Invalid word(s) in submission.",
                user_id, isSystem=False, isError=True)
        else:
            if len(valid_words) == 1:
                resp = ContentFiltering_service.insert_filtered_word(valid_words[0])
                if resp.get("status") == "SUCCESS":
                    messages.success(request, f'Successfully added filtered word ID {resp.get("data", {}).get("id")} to the list.')
                    log_service.log_action(
                        f"Admin user {user_id} successfully added filtered word with ID {resp.get('data', {}).get('id')}",
                        user_id, isSystem=False, isError=False)
                else:
                    messages.error(request, resp.get("message", "An error occurred while adding the word."))
                    log_service.log_action(
                        f"Admin user {user_id} failed to add filtered word: {resp.get('message')}",
                        user_id, isSystem=False, isError=True)
            elif len(valid_words) > 1:
                resp = ContentFiltering_service.insert_multiple_filtered_words(valid_words)
                added_count = resp.get("data", {}).get("added_count", 0)
                if resp.get("status") in ("SUCCESS", "INFO"):
                    if added_count > 0:
                        messages.success(request, resp.get("message"))
                        log_service.log_action(
                            f"Admin user {user_id} successfully added {added_count} filtered words.",
                            user_id, isSystem=False, isError=False)
                    else:
                        messages.warning(request, resp.get("message"))
                else:
                    messages.error(request, resp.get("message", "An error occurred during bulk add."))
                    log_service.log_action(
                        f"Admin user {user_id} failed bulk add filtered words: {resp.get('message')}",
                        user_id, isSystem=False, isError=True)

    # Build redirect URL with parameters
    return _build_redirect_url('manage_wordfilter', {
        'page': page_from_form,
        'search': search_from_form,
        'sort_by': sort_by_from_form,
        'sort_order': sort_order_from_form
    })


# MARK: Update Filtered Word
def process_update_filtered_word(request, context: Dict[str, Any]) -> Any:
    """
    Process updating a filtered word.
    
    Args:
        request: Django HTTP request object
        context: Dictionary containing pagination and search parameters
        
    Returns:
        Django redirect response
    """
    edit_id_from_form = request.POST.get("edit_id")
    content = request.POST.get("edit_filter_content", "").strip()
    
    # Extract form parameters for redirect
    page_from_form = request.POST.get("page", context.get('current_page', 1))
    search_from_form = request.POST.get("search", context.get('search_term', ''))
    sort_by_from_form = request.POST.get("sort_by", context.get('sort_by', 'FilterContent'))
    sort_order_from_form = request.POST.get("sort_order", context.get('sort_order', 'ASC'))

    if not edit_id_from_form or not edit_id_from_form.isdigit():
        messages.error(request, "Invalid ID for editing.")
        # Stay in edit mode for error
        return _build_redirect_url('manage_wordfilter', {
            'edit': edit_id_from_form,
            'page': page_from_form,
            'search': search_from_form,
            'sort_by': sort_by_from_form,
            'sort_order': sort_order_from_form
        })
    
    is_valid, error_msg = validate_filter_content(content)
    user_id = context.get('user_info', {}).get('UserID')
    if is_valid:
        resp = ContentFiltering_service.update_filtered_word_by_id(edit_id_from_form, content)
        if resp.get("status") == "SUCCESS":
            messages.success(request, f'Successfully updated word ID {edit_id_from_form}.')
            log_service.log_action(
                f"Admin user {user_id} successfully updated filtered word ID {edit_id_from_form}.",
                user_id, isSystem=False, isError=False)
            # Success: redirect to list without edit parameter
            return _build_redirect_url('manage_wordfilter', {
                'page': page_from_form,
                'search': search_from_form,
                'sort_by': sort_by_from_form,
                'sort_order': sort_order_from_form
            })
        else:
            messages.error(request, resp.get("message", "An error occurred while updating the word."))
            log_service.log_action(
                f"Admin user {user_id} failed to update filtered word ID {edit_id_from_form}: {resp.get('message')}",
                user_id, isSystem=False, isError=True)
            # Service error: stay in edit mode
            return _build_redirect_url('manage_wordfilter', {
                'edit': edit_id_from_form,
                'page': page_from_form,
                'search': search_from_form,
                'sort_by': sort_by_from_form,
                'sort_order': sort_order_from_form
            })
    else:
        messages.error(request, f"Invalid word for update. {error_msg}")
        log_service.log_action(
            f"Admin user {user_id} failed to update filtered word ID {edit_id_from_form}: Invalid word.",
            user_id, isSystem=False, isError=True)
        # Validation error: stay in edit mode
        return _build_redirect_url('manage_wordfilter', {
            'edit': edit_id_from_form,
            'page': page_from_form,
            'search': search_from_form,
            'sort_by': sort_by_from_form,
            'sort_order': sort_order_from_form
        })


# MARK: Delete Filtered Word
def process_delete_filtered_word(request, context: Dict[str, Any]) -> Any:
    """
    Process deleting a single filtered word.
    
    Args:
        request: Django HTTP request object
        context: Dictionary containing pagination and search parameters
        
    Returns:
        Django redirect response
    """
    filter_id = request.POST.get("delete_id")
    
    # Extract form parameters for redirect
    page_from_form = request.POST.get("page", context.get('current_page', 1))
    search_from_form = request.POST.get("search", context.get('search_term', ''))
    sort_by_from_form = request.POST.get("sort_by", context.get('sort_by', 'FilterContent'))
    sort_order_from_form = request.POST.get("sort_order", context.get('sort_order', 'ASC'))

    if filter_id and filter_id.isdigit():
        resp = ContentFiltering_service.delete_filtered_word_by_id(filter_id)
        user_id = context.get('user_info', {}).get('UserID')
        if resp.get("status") == "SUCCESS":
            messages.success(request, f"Successfully deleted word ID {filter_id}.")
            log_service.log_action(
                f"Admin user {user_id} successfully deleted filtered word ID {filter_id}.",
                user_id, isSystem=False, isError=False)
        else:
            messages.error(request, resp.get("message", f"An error occurred while deleting word ID {filter_id}."))
            log_service.log_action(
                f"Admin user {user_id} failed to delete filtered word ID {filter_id}: {resp.get('message')}",
                user_id, isSystem=False, isError=True)
    else:
        messages.error(request, "Invalid or missing ID for single deletion.")

    # Build redirect URL with parameters
    return _build_redirect_url('manage_wordfilter', {
        'page': page_from_form,
        'search': search_from_form,
        'sort_by': sort_by_from_form,
        'sort_order': sort_order_from_form
    })


# MARK: Bulk Delete Filtered Words
def process_bulk_delete_filtered_words(request, context: Dict[str, Any]) -> Any:
    """
    Process bulk deletion of filtered words.
    
    Args:
        request: Django HTTP request object
        context: Dictionary containing pagination and search parameters
        
    Returns:
        Django redirect response
    """
    selected_ids = request.POST.getlist("selected_words")
    filter_ids_to_delete = [fid for fid in selected_ids if fid and fid.isdigit()]
    
    # Extract form parameters for redirect
    page_from_form = request.POST.get("page", context.get('current_page', 1))
    search_from_form = request.POST.get("search", context.get('search_term', ''))
    sort_by_from_form = request.POST.get("sort_by", context.get('sort_by', 'FilterContent'))
    sort_order_from_form = request.POST.get("sort_order", context.get('sort_order', 'ASC'))

    user_id = context.get('user_info', {}).get('UserID')
    if not filter_ids_to_delete:
        messages.warning(request, "No words selected for deletion.")
    else:
        resp = ContentFiltering_service.delete_filtered_words_by_ids(filter_ids_to_delete)
        if resp.get("status") == "SUCCESS":
            messages.success(request, resp.get("message"))
            log_service.log_action(
                f"Admin user {user_id} successfully bulk deleted filtered words: {len(filter_ids_to_delete)} items.",
                user_id, isSystem=False, isError=False)
        elif resp.get("status") == "NOT_FOUND":
            messages.warning(request, resp.get("message"))
            log_service.log_action(
                f"Admin user {user_id} attempted bulk delete but some IDs not found: {filter_ids_to_delete}",
                user_id, isSystem=False, isError=True)
        else:  # ERROR
            messages.error(request, resp.get("message", "An error occurred during bulk deletion."))
            log_service.log_action(
                f"Admin user {user_id} failed bulk delete filtered words: {resp.get('message')}",
                user_id, isSystem=False, isError=True)

    # Build redirect URL with parameters
    return _build_redirect_url('manage_wordfilter', {
        'page': page_from_form,
        'search': search_from_form,
        'sort_by': sort_by_from_form,
        'sort_order': sort_order_from_form
    })


# MARK: Get Filtered Words For Display
def process_get_filtered_words_for_display(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get filtered words data for display with pagination.
    
    Args:
        context: Dictionary containing pagination and search parameters
        
    Returns:
        Dictionary with filtered words data and pagination info
    """
    per_page = 10
    current_page = context.get('current_page', 1)
    search_term = context.get('search_term', '')
    sort_by = context.get('sort_by', 'FilterContent')
    sort_order = context.get('sort_order', 'ASC')

    # Get total count
    count_response = ContentFiltering_service.get_total_filtered_words_count(search_term=search_term)
    total_filtered_words = 0
    if count_response["status"] == "SUCCESS":
        total_filtered_words = count_response["data"]["total_filtered_words_count"]

    # Get pagination data
    pagination_data = utilities.get_pagination_data(current_page, per_page, total_filtered_words)
    
    # Get filtered words
    response = ContentFiltering_service.get_filtered_words_paginated(
        start_index=pagination_data["start_index"],
        per_page=per_page,
        search_term=search_term,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    filtered_words = response["data"] if response["status"] == "SUCCESS" else []
    
    return {
        **pagination_data,
        'filtered_words': filtered_words,
        'FILTER_CONTENT_REGEX': FILTER_CONTENT_REGEX.replace('^', '').replace('$', ''),  # Remove anchors for HTML pattern
        'FILTER_CONTENT_MAX_LENGTH': FILTER_CONTENT_MAX_LENGTH
    }


# MARK: Get Edit Filtered Word
def process_get_edit_word(edit_id: str) -> Dict[str, Any]:
    """
    Get a filtered word for editing.
    
    Args:
        edit_id: ID of the word to edit
        
    Returns:
        Dictionary with edit word data or empty dict if not found
    """
    if edit_id and edit_id.isdigit():
        edit_response = ContentFiltering_service.get_filtered_word_by_id(edit_id)
        if edit_response["status"] == "SUCCESS":
            return {"edit_word": edit_response["data"]}
    return {}


# MARK: Get All Filtered Words API
def process_get_all_filtered_words_api() -> Dict[str, Any]:
    """
    Process getting all filtered words for API response.
    
    Returns:
        Dictionary with service response for API consumption
    """
    return ContentFiltering_service.get_all_filtered_words()


# MARK: Helper: Build Redirect URL
def _build_redirect_url(url_name: str, params: Dict[str, Any]) -> Any:
    """
    Helper function to build redirect URL with query parameters.
    
    Args:
        url_name: Name of the URL pattern
        params: Dictionary of query parameters
        
    Returns:
        Django redirect response
    """
    base_url = reverse(url_name)
    cleaned_params = {k: v for k, v in params.items() if v is not None and str(v).strip() != ''}
    if cleaned_params:
        return redirect(f"{base_url}?{urlencode(cleaned_params)}")
    return redirect(base_url)
