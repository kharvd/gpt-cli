from jinja2 import Environment, FileSystemLoader
import os


class Renderer:

    def __init__(self):
        current_path = os.path.dirname(os.path.abspath(__file__))
        self.loader = FileSystemLoader(current_path)
        self.env = Environment(loader=self.loader)

    def render(self, template_name, data):
        template = self.env.get_template(template_name)
        return template.render(data=data)
