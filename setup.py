from setuptools import setup

setup(
    name = "fillaridata",
    version = "0.1",
    py_modules = ["fillaridata"],
    install_requires = [
        "Click",
        "appdirs",
        "numpy",
        "pandas",
        "bs4",
        "requests",
        "owslib"
    ],
    entry_points = """
        [console_scripts]
        fillaridata=fillaridata:cli
    """,
)