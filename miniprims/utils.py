import ast
import configparser
import os

DEFAULTS_PATH = os.path.join(os.path.dirname(__file__), 'defaults.ini')


class Config:
    def __init__(self, overrides=None):
        self.parser = configparser.ConfigParser()
        self.parser.read(DEFAULTS_PATH)

        self.overrides = overrides or {}

    def override(self, option, value):
        self.overrides[option] = value

    def default(self, option):
        return ast.literal_eval(self.parser[option]['default'])

    def description(self, option):
        return ast.literal_eval(self.parser[option]['description'])

    def __getitem__(self, option):
        try:
            return self.overrides[option]
        except KeyError:
            return self.default(option)
