import os
from platform import node
import logging


class PromptManager():

    def __init__(self, prompt_name, template_dir="prompt_templates"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.prompt_name = prompt_name
        self.template_dir = template_dir
        self.template = None
        self._load_prompt_template()

    def _load_prompt_template(self):
        """Loads a prompt template from a file."""
        template_file_path = os.path.join(
            self.template_dir, f"{self.prompt_name}.txt")
        try:
            with open(template_file_path, 'r', encoding='utf-8') as f:
                self.template = f.read()
        except FileNotFoundError:
            # Consider how to handle missing templates: raise error, log, or use a default
            # Or raise an error
            self.logger.warning(
                f"Prompt template file not found: {template_file_path}")
            self.template = ""  # Or some default error template
        except Exception as e:
            self.logger.error(
                f"Error loading prompt template {template_file_path}: {e}", exc_info=True)
            self.template = ""  # Or some default error template

    def apply_template(self, inputs):
        if self.template is None or self.template == "":
            # This case should ideally be handled by _load_prompt_template,
            # for example by raising an error if a template couldn't be loaded.
            self.logger.error(
                f"Template for '{self.prompt_name}' not loaded or empty.")
            return ""  # Or raise an error
        return self.template.format(**inputs)
