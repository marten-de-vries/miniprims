import ast
import configparser
import os

import simpy


class Config:
    def __init__(self, overrides=None):
        self.overrides = overrides or {}
        if not hasattr(self, 'defaults'):
            self.load_defaults()

    @classmethod
    def load_defaults(cls):
        cls.defaults, cls.descriptions = {}, {}
        parser = configparser.ConfigParser()
        parser.read(os.path.join(os.path.dirname(__file__), 'defaults.ini'))
        for option in parser.sections():
            cls.defaults[option] = ast.literal_eval(parser[option]['default'])

            try:
                description = parser[option]['description']
            except KeyError:
                cls.descriptions[option] = ''
            else:
                cls.descriptions[option] = ast.literal_eval(description)

    def override(self, option, value):
        self.overrides[option] = value

    def description(self, option):
        self.descriptions[option]

    def __getitem__(self, option):
        try:
            return self.overrides[option]
        except KeyError:
            return self.defaults[option]


class Environment(simpy.Environment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_reset = 0

    @property
    def time(self):
        return self.now - self.last_reset
