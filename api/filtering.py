"""
Advanced API Filtering System
============================

Comprehensive filtering system for API endpoints with support for:
- Date range filtering (DateTimeField, DateField)
- Text search filtering (CharField)
- Numeric range filtering (FloatField, IntegerField)
- Clean parameter parsing and validation
"""

import json
from datetime import datetime, date
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime, parse_date


class FilterError(Exception):
    """Custom exception for filter-related errors"""
    pass


def get_field_type(model, field_name):
    """
    Get the Django field type for a given field name in a model
    """
    try:
        field = model._meta.get_field(field_name)
        return type(field)
    except:
        return None


def is_date_field(field_type):
    """Check if field is a date/datetime field"""
    return field_type in [models.DateTimeField, models.DateField]


def is_text_field(field_type):
    """Check if field is a text field"""
    return field_type in [models.CharField, models.TextField]


def is_numeric_field(field_type):
    """Check if field is a numeric field"""
    return field_type in [models.FloatField, models.IntegerField, models.BigIntegerField]


def parse_date_value(date_str):
    """
    Parse a date string into a datetime object
    Supports multiple formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, etc.
    """
    if not date_str:
        return None
    
    # Try parsing as datetime first
    dt = parse_datetime(date_str)
    if dt:
        return dt
    
    # Try parsing as date
    d = parse_date(date_str)
    if d:
        return datetime.combine(d, datetime.min.time())
    
    # Try manual parsing for common formats
    try:
        # YYYY-MM-DD
        if len(date_str) == 10 and date_str.count('-') == 2:
            return datetime.strptime(date_str, '%Y-%m-%d')
        # YYYY-MM-DD HH:MM:SS
        elif len(date_str) == 19 and date_str.count('-') == 2 and date_str.count(':') == 2:
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        pass
    
    raise FilterError(f"Invalid date format: {date_str}. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")


def apply_date_range_filter(queryset, field_name, date_range):
    """
    Apply date range filtering to a queryset
    
    date_range format:
    {
        "start": "2024-01-01",
        "end": "2024-12-31"
    }
    """
    if not isinstance(date_range, dict):
        raise FilterError("Date range must be a dictionary with 'start' and/or 'end' keys")
    
    filters = {}
    
    if 'start' in date_range:
        start_date = parse_date_value(date_range['start'])
        if start_date:
            filters[f'{field_name}__gte'] = start_date
    
    if 'end' in date_range:
        end_date = parse_date_value(date_range['end'])
        if end_date:
            # For end date, we want to include the entire day
            # So we set it to end of day
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            filters[f'{field_name}__lte'] = end_date
    
    if filters:
        return queryset.filter(**filters)
    
    return queryset


def apply_text_search_filter(queryset, field_name, search_value):
    """
    Apply text search filtering to a queryset
    
    search_value can be:
    - String: exact match
    - {"contains": "text"}: contains search
    - {"icontains": "text"}: case-insensitive contains
    - {"startswith": "text"}: starts with
    - {"istartswith": "text"}: case-insensitive starts with
    - {"endswith": "text"}: ends with
    - {"iendswith": "text"}: case-insensitive ends with
    """
    if isinstance(search_value, str):
        # Simple exact match
        return queryset.filter(**{field_name: search_value})
    
    elif isinstance(search_value, dict):
        # Advanced text search
        for operator, value in search_value.items():
            if operator in ['contains', 'icontains', 'startswith', 'istartswith', 'endswith', 'iendswith']:
                return queryset.filter(**{f'{field_name}__{operator}': value})
            else:
                raise FilterError(f"Invalid text search operator: {operator}")
    
    else:
        raise FilterError("Text search value must be a string or dictionary")


def apply_numeric_range_filter(queryset, field_name, numeric_range):
    """
    Apply numeric range filtering to a queryset
    
    numeric_range format:
    {
        "min": 100,
        "max": 1000
    }
    or
    {
        "gte": 100,  # greater than or equal
        "lte": 1000, # less than or equal
        "gt": 100,   # greater than
        "lt": 1000   # less than
    }
    """
    if not isinstance(numeric_range, dict):
        raise FilterError("Numeric range must be a dictionary")
    
    filters = {}
    
    # Support both min/max and gte/lte/gt/lt formats
    if 'min' in numeric_range:
        filters[f'{field_name}__gte'] = numeric_range['min']
    if 'max' in numeric_range:
        filters[f'{field_name}__lte'] = numeric_range['max']
    
    # Direct operators
    for op in ['gte', 'lte', 'gt', 'lt']:
        if op in numeric_range:
            filters[f'{field_name}__{op}'] = numeric_range[op]
    
    if filters:
        return queryset.filter(**filters)
    
    return queryset


def apply_advanced_filter(queryset, model, field_name, filter_value):
    """
    Apply advanced filtering based on field type and filter value
    """
    field_type = get_field_type(model, field_name)
    
    if not field_type:
        raise FilterError(f"Field '{field_name}' not found in model")
    
    # Date range filtering
    if is_date_field(field_type):
        if isinstance(filter_value, dict) and ('start' in filter_value or 'end' in filter_value):
            return apply_date_range_filter(queryset, field_name, filter_value)
        else:
            # Single date value
            date_val = parse_date_value(filter_value)
            return queryset.filter(**{field_name: date_val})
    
    # Text search filtering
    elif is_text_field(field_type):
        return apply_text_search_filter(queryset, field_name, filter_value)
    
    # Numeric range filtering
    elif is_numeric_field(field_type):
        if isinstance(filter_value, dict) and any(op in filter_value for op in ['min', 'max', 'gte', 'lte', 'gt', 'lt']):
            return apply_numeric_range_filter(queryset, field_name, filter_value)
        else:
            # Single numeric value
            return queryset.filter(**{field_name: filter_value})
    
    # Default: simple equality
    else:
        return queryset.filter(**{field_name: filter_value})


def parse_filter_parameters(filter_param):
    """
    Parse and validate filter parameters from JSON string
    
    Expected format:
    {
        "field1": "value1",
        "field2": {"contains": "text"},
        "date_field": {"start": "2024-01-01", "end": "2024-12-31"},
        "numeric_field": {"min": 100, "max": 1000}
    }
    """
    if not filter_param:
        return {}
    
    try:
        filters = json.loads(filter_param)
    except json.JSONDecodeError as e:
        raise FilterError(f"Invalid JSON in filter parameter: {str(e)}")
    
    if not isinstance(filters, dict):
        raise FilterError("Filter parameter must be a JSON object")
    
    return filters


def apply_filters_to_queryset(queryset, model, filter_param):
    """
    Apply all filters to a queryset based on filter parameters
    
    Args:
        queryset: Django queryset to filter
        model: Django model class
        filter_param: JSON string with filter parameters
    
    Returns:
        Filtered queryset
    """
    if not filter_param:
        return queryset
    
    try:
        filters = parse_filter_parameters(filter_param)
    except FilterError as e:
        raise FilterError(f"Filter parsing error: {str(e)}")
    
    for field_name, filter_value in filters.items():
        try:
            queryset = apply_advanced_filter(queryset, model, field_name, filter_value)
        except FilterError as e:
            raise FilterError(f"Error filtering field '{field_name}': {str(e)}")
        except Exception as e:
            raise FilterError(f"Unexpected error filtering field '{field_name}': {str(e)}")
    
    return queryset


def get_filter_examples():
    """
    Get examples of filter usage for documentation
    """
    return {
        "basic_examples": {
            "exact_match": {
                "asset_code": "KR_BW_19"
            },
            "text_search": {
                "asset_name": {"contains": "KR_BW"}
            },
            "date_range": {
                "day_date": {"start": "2024-01-01", "end": "2024-12-31"}
            },
            "numeric_range": {
                "daily_prod_rec": {"min": 100, "max": 1000}
            }
        },
        "advanced_examples": {
            "multiple_filters": {
                "asset_code": {"contains": "KR_BW"},
                "day_date": {"start": "2024-01-01", "end": "2024-12-31"},
                "daily_prod_rec": {"gte": 100}
            },
            "text_operators": {
                "asset_name": {"icontains": "solar"},
                "country": {"startswith": "KR"}
            },
            "numeric_operators": {
                "daily_prod_rec": {"gte": 100, "lt": 1000},
                "dc_capacity_mw": {"gt": 10}
            }
        }
    }
