#!/usr/bin/env python

"""This tool creates and maintains data for the Fillariennustin
project. """

__author__ = "Joonas Häkkinen"
__version__ = 0.1

import logging

import click
from appdirs import user_log_dir

from classes.Config import Config
from classes.Datafile import Datafile
from modules.data import update_data


# Global options
@click.group()
@click.option("--file", "-f", type=click.Path(), default="./data.h5",
              help="Path to data file.")
@click.option("--logfile", "-l", type=click.Path(),
              default=user_log_dir("fillaridata.log"),
              help="Path to log file.")
def cli(file, logfile):
    """Initialise program with given parameters."""
    global df, config

    # Set up logging
    logging.basicConfig(filename=logfile, level=logging.INFO,
                        format="%(asctime)s - %(levelname)s: %(message)s")

    # Make sure we have an API key for FMI's open data service
    config = Config("~/.fillaridata", "main.conf")
    api_key = config.value("FMI", "api_key")

    if api_key is None:
        click.echo("API key for FMI's open data service was not found. "
                   "Without one, fetching new data will fail. Your API key "
                   "will be saved in '{}'.".format(config.path))
        new_key = click.prompt("Please enter your API key", type=str)
        config.set("FMI", "api_key", new_key)

    # Load the datafile
    df = Datafile(file)


# COMMAND: update
@cli.command(help="Update or create data file.")
@click.option("--limit", "-l", default=0,
              help="Set limit for maximum amount of rows to fetch and save.")
@click.option("--batch", "-b", default=500, help="Maximum batch size to "
                                                 "process. Data is saved to "
                                                 "file at this interval.")
@click.option("--source", "-s", type=click.Path(),
              default="http://dev.hsl.fi/tmp/citybikes/",
              help="Path to source data.")
def update(limit, batch, source):
    update_data(df, config, limit, batch, source)


# COMMAND: info
@cli.command(help="Show information about current data file.")
def info():
    df.print_info()
