#!/usr/bin/env python

"""This class represents a configuration file  and offers ways to
interact with that file."""

__author__ = "Joonas Häkkinen"

import configparser
import os


class Config:
    def __init__(self, conf_dir, filename):
        """Open config file or create it if not found.

        Arguments:
        file -- Valid path to configuration file.
        """
        if conf_dir == "":
            conf_dir = "./"

        conf_dir = os.path.expanduser(conf_dir)
        self.path = os.path.join(conf_dir, filename)

        if not os.path.isfile(self.path):
            os.makedirs(conf_dir, exist_ok=True)
            f = open(self.path, "x")
            f.close()

        self.config = configparser.ConfigParser()
        self.config.read(self.path)

    def value(self, section, key):
        """Return value of requested configuration parameter.

        Format compatible with Python's configparser is assumed. If
        either the *section* or *key* are not found, None is returned.

        Arguments:
        section -- Name of the section where the requested parameter is
        located in.
        key -- Name of the parameter requested.
        """
        if section not in self.config:
            return None

        if key not in self.config[section]:
            return None

        return self.config[section][key]

    def set(self, section, key, value):
        """Set configuration parameter to given value.

        Format compatible with Python's configparser is assumed. The
        given *key* is created, if not found.

        Arguments:
        section -- Name of the section where the target parameter is
        located in.
        key -- Name of the target parameter.
        value -- New value for the target parameter.
        """
        if section not in self.config:
            self.config[section] = {}

        self.config[section][key] = value

        with open(self.path, "w") as configfile:
            self.config.write(configfile)
