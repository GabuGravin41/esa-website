from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key."""
    return dictionary.get(key, 0)

@register.filter
def add_class(field, css_classes):
    """Add CSS classes to a form field."""
    return field.as_widget(attrs={"class": css_classes}) 