# fillaridata
 
This is a python command line utility to create and maintain the dataset for
an upcoming prediction project. It combines city bike and weather data for 
Helsinki, Finland into a HDF5 storage file.

The program reads new city bike data (all, if no existing datafile is found) 
from the source. Then weather data is fetched for the corresponding period 
and added to the bike data. Finally, this dataset is appended to an existing
dataset or a new file created.

## Status

**FUNCTIONAL**

This project is currently functional and can be used for the purposes 
outlined above. Logging and UI may be missing some features, but sans bigger
errors, everything should work just fine.

If you run into problems, they are most likely related to the bike data. 
Please see section _Data sources_ for further discussion. 

## Data sources

### City bike data

City bike data is offered by HSL (Helsinki Regional Transport Authority). At
the time of writing, the data is distributed under [Creative Commons 
Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/deed.en)
licence. However, you should naturally [make sure](https://www.hsl.fi/en/opendata)
before using the data.  

City bike data by default is sourced from HSL's historical storage 
[here](http://dev.hsl.fi/tmp/citybikes/). They also offer an official 
GraphQL API which, however, serves out only current data. As the historical 
storage appears to be updated in real-time, I have opted to use only this 
source for the time being.

While their historical storage has in general worked well at least during 
summer 2017, it does exhibit corrupted data etc. every now and then. _**If you 
run into problems, always check this source's status first!**_

Data can be fetched directly from HSL's storage or downloaded first and used
from a local directory. The latter is especially useful if you need to 
incorporate the older data that is offered as zip files in the storage (see 
_Usage_ for more).

I strongly recommend backing up any data you've gathered with this tool, 
since HSL has already managed to lose the data for July 2017.

_Ideally, this tool would allow for initial data gathering using the 
historical storage and then maintaining the data through the more robust and 
official GraphQL API. You're welcome to implement this :)_

### Weather data

Weather data is gathered through FMI's (Finnish Meteorological Institute) 
open data service. At the time of writing, they use the same licence as HSL 
above. See [here](http://en.ilmatieteenlaitos.fi/open-data-licence) for more
information.

Historical data is accessed through _OGC Web Feature Service (WFS)_, whatever
that is.

The following attributes are recorded (source data is at 10-minute intervals):

* Temperature, current (°C)
* Wind speed, 10-minute average (m/s)
* Rainfall, 1-hour average (mm)
* Pressure at sea level, current (mbar)

_**Note:**_ _I'm not happy with my implementation of parsing WFS data (nor 
with WFS/owslib in general). I'd be extremely happy to hear about better 
solutions._

## Resulting dataset

The resulting HDF5 file includes one key, `data`, which consists of a Pandas
DataFrame with the following features as columns:

* `avl_bikes`
* `coordinates`
* `free_slots`
* `operative`
* `style`
* `total_slots` 
* `P_SEA`
* `R_1H`
* `T`
* `WS_10MIN`

The DataFrame has a MultiIndex with levels `date_utc` and `name`, respectively
(the latter refers to bike station name). With the current amount of city 
bike stations, this means ~150 rows with unique `name`'s per one entry in 
`date_utc`. (This also means that, e.g., `fillaridata update --limit=1` will
actually add around 150 rows to the datafile.)
 
The bike data is recorded every minute resulting in roughly 216,000 rows/day
 ≈ 6.5M rows/month. 

## Installation

I recommend creating a conda virtualenv and installing this program using pip:

    $ conda create -n fillaridata
    $ source activate fillaridata
    $ conda install pip
    $ pip install https://github.com/joonashak/fillaridata/archive/master.zip

### Development mode

To install in editable mode:

    pip install -e /path/to/package

## Usage

Update data, create new file if necessary:

    fillaridata update
    
Print information about current dataset:

    fillaridata info

For more help about command line options, see `fillaridata --help` and/or
`fillaridata <command> --help`.

### Alternative source (bike data)

To fetch bike data from an alternative source, use the option `-s` or 
`--source` for `fillaridata update`.

For example, to incorporate older data from the zip files in HSL's data 
storage, download and extract the zip's contents to an empty folder and 
do:

    fillaridata update --source=/path/to/source/folder/

### Memory issues

It's quite easy to run into memory issues in limited environments, such as 
VPS's with a gig or two of RAM, as this tool loads the whole datafile into 
memory. Use the `--first` and `--limit` options in combination to create 
smaller files. Limiting the files to 20,000 timestamps should be small 
enough to run comfortably on 2GB RAM.

For now, this is very manual and the file needs to be switched by hand every
two weeks or so. 

## TODO

Here's a random TODO list of things that could be improved:

* Add HSL's GraphQL API as a source.
* Refactor logging and output functionality to its own module.
* Add option to fetch only bike data.
* Add progress bar or another way of keeping the user informed, e.g., during
 manually creating the initial file.
* My use of "date" and "row" is probably very confusing and should be 
clarified. _(Slowly migrating to using "timestamp".)_
* Automatic splitting into multiple datafiles for easier use in low-memory 
environments.

You're welcome to help :)

## Changes

* **2017-08-24:** Added `--first` option to ignore earlier data.