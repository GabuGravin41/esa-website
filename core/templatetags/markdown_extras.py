import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def markdown_to_html(text):
    """
    Convert markdown text to safe HTML
    
    Usage: {{ content|markdown_to_html }}
    """
    if text:
        # Convert markdown to HTML with extensions
        html = markdown.markdown(
            text,
            extensions=[
                'markdown.extensions.fenced_code',
                'markdown.extensions.tables',
                'markdown.extensions.nl2br',
                'markdown.extensions.toc',
                'markdown.extensions.codehilite',
            ]
        )
        return mark_safe(html)
    return "" 