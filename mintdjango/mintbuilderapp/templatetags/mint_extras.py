from django.template.defaulttags import register

# I need this custom tag to access a dictionary with a variable...
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)