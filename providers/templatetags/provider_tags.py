from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get a dictionary value by key.
    Usage: {{ dictionary|get_item:key }}
    """
    return dictionary.get(key)


@register.filter
def split(value, separator='.'):
    """
    Split a string by separator.
    Usage: {{ "book.example.com"|split:"." }} returns ['book', 'example', 'com']
    """
    if not value:
        return []
    return value.split(separator)


@register.filter
def get_subdomain(domain):
    """
    Get the subdomain part from a full domain.
    Usage: {{ "book.example.com"|get_subdomain }} returns 'book'
           {{ "example.com"|get_subdomain }} returns '@'
    """
    if not domain:
        return '@'
    parts = domain.split('.')
    if len(parts) > 2:
        return parts[0]
    return '@'


@register.filter
def contrast_color(hex_color):
    """
    Returns 'white' or 'dark' based on the brightness of the hex color.
    Usage: {{ color|contrast_color }}
    """
    if not hex_color:
        return 'white'
    
    # Remove # if present
    hex_color = hex_color.lstrip('#')
    
    # Convert to RGB
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except (ValueError, IndexError):
        return 'white'
    
    # Calculate perceived brightness (ITU-R BT.709)
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    
    return 'dark' if brightness > 150 else 'white'


@register.filter
def darken_color(hex_color, percent=20):
    """
    Darken a hex color by a percentage.
    Usage: {{ color|darken_color:30 }}
    """
    if not hex_color:
        return '#4c1d95'  # Default dark purple
    
    # Remove # if present
    hex_color = hex_color.lstrip('#')
    
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        percent = int(percent)
    except (ValueError, IndexError):
        return '#4c1d95'
    
    # Darken each channel
    factor = 1 - (percent / 100)
    r = max(0, int(r * factor))
    g = max(0, int(g * factor))
    b = max(0, int(b * factor))
    
    return f'#{r:02x}{g:02x}{b:02x}'


@register.filter
def lighten_color(hex_color, percent=20):
    """
    Lighten a hex color by a percentage.
    Usage: {{ color|lighten_color:20 }}
    """
    if not hex_color:
        return '#a855f7'  # Default light purple
    
    # Remove # if present
    hex_color = hex_color.lstrip('#')
    
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        percent = int(percent)
    except (ValueError, IndexError):
        return '#a855f7'
    
    # Lighten each channel
    factor = percent / 100
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    
    return f'#{r:02x}{g:02x}{b:02x}'
