#!/usr/bin/env python

"""Functionality to gather and format city bike data from HSL for
Fillariennustin. """

__author__ = "Joonas Häkkinen"

import logging
import os
import re
import sys
from urllib.parse import urlparse

import click
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from requests import get

from modules.fmi import add_weather_data


def update_data(datafile, config, limit, batch, source):
    """Updates the datafile with new data.

    Data after the last entry in *datafile* is fetched and appended to
    the file. Data is saved to file at *batch* intervals to limit
    memory use.

    Note that 'date' refers to a unique value of date, which are
    recorded at 1-minute intervals (i.e., an hour has 60 such 'dates').

    :param datafile: Datafile instance
    :param config: Config instance
    :param limit: Number of maximum dates to add.
    :param batch: How many dates to process at between saving the
    datafile.
    :param source: URL or local path to a folder containing source data
    files named in the format above.
    :return: None
    """
    filenames = __get_links(source, datafile.last_date())
    api_key = config.value("FMI", "api_key")

    if limit > 0:
        last = limit + 1 if limit < len(filenames) else len(filenames)
        filenames = filenames[:last]

    slices = np.arange(0, len(filenames), batch)

    for i, start in enumerate(slices):
        stop = slices[i + 1] if i < len(slices) - 1 else len(filenames) - 1

        new_data = __get_bike_data(source, filenames[start:stop])
        new_data = add_weather_data(new_data, api_key)
        datafile.update(new_data)

    return None


def __get_links(source, start_after):
    """Return a list of filenames for fetching new data.

    Returns a list of filenames parsed from *source*. Only names of the
    form 'stations_yyyymmddThhmmssZ' and corresponding to a date and
    time later than *start_after* are included.

    Arguments:
    source -- URL or local path to a folder containing source data files
    named in the format above.
    start_after -- The date and time (UTC) of the last row in an
    existing datafile.
    """

    # Form the list of source files
    if urlparse(source).scheme == "http":
        links = BeautifulSoup(get(source).content, "lxml").find_all("a")
        names = [link['href'] for link in links]
        msg = "links"
    elif os.path.isdir(source):
        names = os.listdir(source)
        msg = "files"
    else:
        logging.error("Invalid source path {}".format(source))
        click.echo(click.style(" * Source path is not a valid HTTP address "
                               "or local folder, quitting.", fg="red",
                               bold=True))
        sys.exit()

    click.echo(click.style(" * {:,} {} found".format(len(names), msg),
                           fg="green"))

    # Check that all filenames match the date format we expect
    # (N.B.: trailing 'Z' denotes UTC time
    matches = [name for name in names if re.match("stations_\d{8}T\d{6}Z",
                                                  name)]

    if len(matches) > 1:
        click.echo(click.style(" * {:,} filenames are in correct format"
                               .format(len(matches)), fg="green"))
    else:
        logging.error("Zero filenames match the date format ({:,} {} tested)"
                      .format(len(names), msg))
        click.echo(click.style(" * No filenames mathing the required date "
                               "format found, quitting.", fg="red", bold=True))
        sys.exit()

    # Return only new filenames
    due = [f for f in matches if pd.to_datetime(f[9:]) > start_after]

    if len(due) == 0:
        logging.info("No new files found, quitting.")
        click.echo(click.style(" * No new data found, quitting.", fg="green"))
        sys.exit()

    return due


def __get_bike_data(source, files):
    """Merge and return citybike data.

    Citybike data located in *files in *source* directory is fetched,
    merged and preprocessed for use as Fillariennustin project's
    dataset.
    """
    data = pd.DataFrame()
    failures = 0

    for file in files:
        full_path = os.path.join(source, file)

        try:
            new_data = pd.read_json(full_path)
            new_data = new_data.result.apply(pd.Series)
            new_data['date_utc'] = pd.Timestamp(file[9:])
            new_data.set_index(['date_utc', 'name'], inplace=True)
            data = data.append(new_data)
        except:
            failures += 1
            continue

    if failures > 0:
        logging.warning("{} failures in __get_bike_data()".format(failures))
        click.echo(click.style(" * Data for {} dates could not be "
                               "processed".format(failures), fg="red",
                               bold=True))

    return data