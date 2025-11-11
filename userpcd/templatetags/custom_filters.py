from django import template

register = template.Library()


@register.filter(name='count_by_status')
def count_by_status(queryset_or_list, status_value):
    """
    Count items in a queryset or list that have a specific status.
    Usage: {{ items|count_by_status:"ativa" }}
    """
    try:
        if hasattr(queryset_or_list, 'filter'):
            # It's a queryset
            return queryset_or_list.filter(status=status_value).count()
        else:
            # It's a list or other iterable
            return sum(1 for item in queryset_or_list if hasattr(item, 'status') and item.status == status_value)
    except (AttributeError, TypeError):
        return 0
