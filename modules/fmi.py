#!/usr/bin/env python

"""Utilities to get weather data from FMI's (Finnish Meteorological
Institute) open data service. """

__author__ = "Joonas Häkkinen"

import xml.etree.ElementTree as ET

import pandas as pd
from owslib.wfs import WebFeatureService


def add_weather_data(data, api_key):
    """Add weather data from FMI to DataFrame.

    This module looks for the first and last dates in given DataFrame's
    DatetimeIndex and fetches weather data from FMI for that period.
    The weather data is then appended to the original data and the
    resulting DataFrame returned.

    Arguments:
    data -- Pandas DataFrame with a DatetimeIndex.
    api_key -- API key to FMI's open data service.
    """

    # Get weather data for the range
    start = data.index.min()[0]
    stop = data.index.max()[0]

    weather_data = __get_weather_data(start, stop, "1d", api_key)

    # Concatenate weather data to all rows of original data
    weather_data = weather_data.reindex(data.index.get_level_values(0),
                                        method="nearest")
    weather_data.index = data.index
    data = pd.concat([data, weather_data], axis=1)

    return data


def __get_weather_range(start, stop, api_key):
    """Get Helsinki's weather data between start and stop.

    Return DataFrame of Helsinki's weather data between start and stop
    (Zulu time, i.e., UTC). Includes features: temperature, wind speed,
    sea-level barometric pressure and 1-hour rainfall.

    Maximum interval between *start* and *stop* is 168 hrs = 7 days.
    However, intervals over 1-2 days tend to experience HTTP timeouts.

    Returns None, if getting data from WFS fails.

    Arguments:
    start -- First date (Pandas Timestamp)
    stop -- Last date (Pandas Timestamp)
    api_key -- API key to FMI's open data service.
    """

    # Connect to FMI WFS service and load raw GML data
    addr = "http://data.fmi.fi/fmi-apikey/" + api_key + '/wfs'
    query_id = "fmi::observations::weather::cities::simple"
    start = pd.Timestamp(start).strftime("%Y-%m-%dT%H:%M:%SZ")
    stop = pd.Timestamp(stop).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {'starttime': str(start), 'endtime': str(stop)}

    try:
        wfs = WebFeatureService(addr, version="2.0.0")
        res = wfs.getfeature(storedQueryID=query_id, storedQueryParams=params)
    except TimeoutError:
        print("timeout")
        return None
    except:
        print("muu")
        return None

    data = pd.DataFrame()
    targets = ['T', 'WS_10MIN', 'P_SEA', 'R_1H']
    row_data = {}

    # Parse through the tree structure toward target data
    root = ET.fromstring(res.read())
    for member in root.findall("{http://www.opengis.net/wfs/2.0}member"):
        bs = member.find("{http://xml.fmi.fi/schema/wfs/2.0}BsWfsElement")
        location = bs.find("{http://xml.fmi.fi/schema/wfs/2.0}Location")
        point = location.find("{http://www.opengis.net/gml/3.2}Point")
        pos = point.find("{http://www.opengis.net/gml/3.2}pos")

        # Limit to Helsinki's coordinates (note trailing space)
        if pos.text == "60.17523 24.94459 ":
            pname = bs.find(
                "{http://xml.fmi.fi/schema/wfs/2.0}ParameterName").text
            pvalue = float(bs.find(
                "{http://xml.fmi.fi/schema/wfs/2.0}ParameterValue").text)

            # Parse parameter values
            if pname in targets:
                row_data[pname] = pvalue

            # Once all parameters have been recorded, update the DataFrame
            if len(row_data) == len(targets):
                date = pd.Timestamp(
                    bs.find("{http://xml.fmi.fi/schema/wfs/2.0}Time").text)
                row = pd.DataFrame(row_data, index=[date])
                data = data.append(row)
                row_data = {}

    return data


def __get_weather_data(start, stop, step, api_key):
    """Executes __get_weather_range() in given intervals.

    Note that for FMI, the maximum interval that can be fetched at once
    is 7 days. You may experience HTTP read timeouts before that. The
    original author was able to use only up to '2d' interval, with '1d'
    appearing to be a robust selection.

    Arguments:
    start -- First date (Pandas Timestamp)
    stop -- Last date (Pandas Timestamp)
    step -- Interval length, use the format for pandas.date_range()'s
    freq argument (e.g., '1d' for one day).
    api_key -- API key to FMI's open data service.
    """
    data = pd.DataFrame()
    start = pd.Timestamp(start)
    # Add 10 minutes to stopping time to cover for any rounding
    stop = pd.Timestamp(stop) + pd.Timedelta(minutes=10)

    for range_start in pd.date_range(start, stop, freq=step):
        range_stop = range_start + pd.Timedelta(step)

        if range_stop > stop:
            range_stop = stop

        data = data.append(__get_weather_range(range_start, range_stop,
                                               api_key))

    """1-hour rain (R_1H) is recorded only on the hour. If this source 
   is used when making predictions, the data available will reflect 
   this restriction, thus we can simply fill the NaN's with previous 
   values:
   """
    data.R_1H.fillna(method="ffill", inplace=True)
    # Fill first rows if data doesn't begin on the hour
    data.R_1H.fillna(method="bfill", inplace=True)

    return data[~data.index.duplicated(keep="first")]
