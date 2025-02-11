from collections import OrderedDict
from configparser import ConfigParser
import os


class ConfigParserMultiValues(OrderedDict):

    def __setitem__(self, key, value):
        if key in self and isinstance(value, list):
            self[key].extend(value)
        else:
            super().__setitem__(key, value)

    @staticmethod
    def getlist(value):
        return value.split(os.linesep)


class Config:
    def __init__(self):
        config = ConfigParser(
            strict=False,
            empty_lines_in_values=False,
            dict_type=ConfigParserMultiValues,
            converters={"list": ConfigParserMultiValues.getlist},
        )

        config.read("config.ini")
        self.config = config

    @property
    def paths(self):
        try:
            return self.config.getlist("paths", "path")
        except Exception:
            return []

    @property
    def prefix(self):
        try:
            return self.config.get("prefix", "prefix")
        except Exception:
            return None
