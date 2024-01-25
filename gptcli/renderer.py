from jinja2 import Template


def render(template_content, data):
    template = Template(template_content)
    return template.render(data=data)
