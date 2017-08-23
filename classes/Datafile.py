#!/usr/bin/env python

"""This class represents the data file used by Fillariennustin. Format
is HDF5. Functionality to update the data and view information about
stored data are provided."""

__author__ = "Joonas Häkkinen"

import logging
from os.path import isfile

import click
import pandas as pd


class Datafile:
    def __init__(self, path):
        """Load data from file in *path* and return a Datafile object
        representing that data set.
        """
        if not isfile(path):
            click.echo(click.style(" * Data file not found.", fg="red",
                                   bold=True))
            logging.warning("Data file not found at {}"
                            .format(click.format_filename(path)))

        self.path = path
        self.data = self.__get_data()

    def __get_data(self):
        """Returns contents of the data file (HDF format) if file is
        found, otherwise None.
        """
        if isfile(self.path):
            store = pd.HDFStore(self.path)

            if "/data" not in store.keys():
                click.echo(click.style(" * No data found in data file",
                                       fg="red", bold=True))
                logging.warning("Data file did not include key 'data'")
                return None

            data = store['data']
            store.close()
            return data
        else:
            return None

    def update(self, new_data):
        """Append *new_data* to end of *datafile* (HDF5)."""
        if not isfile(self.path):
            click.echo(click.style(" * Creating data file: {}"
                                   .format(click.format_filename(self.path)),
                                   fg="green"))
            logging.info("New data file created at {}"
                         .format(click.format_filename(self.path)))

        store = pd.HDFStore(self.path)

        if "/data" not in store.keys():
            data = pd.DataFrame()
        else:
            data = store['data']
            data.index.levels[0].tz = None

        new_data.index.levels[0].tz = None
        store['data'] = data.append(new_data)
        store.data.reset_index(inplace=True)
        store.close()

        # Log the changes that we just wrote
        rows = len(new_data)
        dates = len(new_data.index.levels[0])
        logging.info("Wrote {:,} rows ({:,} unique timestamps) to {}"
                     .format(rows, dates, click.format_filename(self.path)))

    def print_info(self):
        """Print information about current data file."""
        if self.data is None:
            click.echo(click.style(" * Exiting, no data found.", fg="red",
                                   bold=True))
            logging.error("No data found for Datafile.print_info()")
            raise SystemExit

        click.echo("Data file: {}".format(self.path))
        click.echo("Number of rows: {:,}".format(self.data.shape[0],
                                                 grouping=True))
        click.echo("First entry: {}".format(self.data.index.min()[0]))
        click.echo("Last entry: {}".format(self.last_date()))

    def last_date(self):
        """Return the date of the last entry in this Datafile."""
        if self.data is None:
            return pd.to_datetime("20160101T000000Z")
        else:
            return self.data.index.max()[0]
