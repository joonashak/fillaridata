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


def update_data(datafile, config, first, limit, batch, source):
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
    api_key = config.value("FMI", "api_key")

    filenames = __get_filenames(source, datafile.last_date())
    batches = __trim_split_filenames(filenames, first, limit, batch)

    for filenames in batches:
        new_data = __get_bike_data(source, filenames)
        new_data = __generate_missing_rows(new_data)
        new_data = add_weather_data(new_data, api_key)
        datafile.update(new_data)

    return None


def __get_filenames(source, start_after):
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
            new_data['date_utc'] = pd.Timestamp(file[9:]).replace(second=0)
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


def __trim_split_filenames(filenames, first, limit, batch):
    """Apply --first, --limit and --batch options to list of filenames.

    Takes a list of filenames and applies the mentioned command line
    options to that list. Entries corresponding to timestamps before
    *first* are dropped and the list is truncated to maximum length of
    *limit*. The resulting list is then split into lists containing at
    maximum *batch* members and the resulting list of lists is
    returned.

    :param filenames: List of properly formatted filenames.
    :param first: First timestamp to include in result.
    :param limit: Maximum number of filenames in result.
    :param batch: Size limit for sublists.
    :return: List of lists of filename strings.
    """

    # Apply --first option by dropping earlier filenames
    date_format = "stations_%Y%m%dT%H%M%SZ"
    filenames = \
        [f for f in filenames
            if pd.to_datetime(f, format=date_format) >= pd.to_datetime(first)]

    # Apply --limit option by truncating the list of filenames
    if limit > 0:
        last = limit if limit < len(filenames) else len(filenames)
        filenames = filenames[:last]

    # Split to batches (--batch)
    return [filenames[x:x + batch] for x in range(0, len(filenames), batch)]


def __generate_missing_rows(data):
    """Generate missing rows to ensure *data* has a row for each minute.

    :param: data: Pandas DataFrame with a proper MultiIndex.
    :return: Input dataframe appended with missing rows.
    """

    start = data.index.min()[0]
    stop = data.index.max()[0]

    # New index
    date_utc = pd.date_range(start, stop, freq="min")
    name = data.index.levels[1].values
    new_index = pd.MultiIndex.from_product([date_utc, name],
                                           names=["date_utc", "name"])

    return data.reindex(index=new_index)