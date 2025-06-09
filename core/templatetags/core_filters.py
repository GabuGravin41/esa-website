from django import template
import markdown
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key."""
    return dictionary.get(key, 0)

@register.filter
def add_class(field, css_classes):
    """Add CSS classes to a form field."""
    return field.as_widget(attrs={"class": css_classes}) 

@register.filter
def markdown_to_html(text):
    return mark_safe(markdown.markdown(text))