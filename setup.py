import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name = "PyNavienSmartControl",
    version = "1.0.0",
    author = "Brian Rudy",
    author_email = "brudy@praecogito.com",
    description = "A Python module and tools for getting information about and controlling your Navien tankless water heater, combi-boiler or boiler connected via NaviLink.",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/rudybrian/PyNavienSmartControl",
    project_urls = {
        "Bug Tracker": "https://github.com/rudybrian/PyNavienSmartControl/issues",
    },
    classifiers = [
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: OS Independent",
        "Topic :: Internet",
        "Topic :: System :: Hardware :: Hardware Drivers",
        "Development Status :: 3 - Alpha",
    ],
    package_dir = {"": "python/shared"},
    packages=setuptools.find_packages(where="python/shared"),
    python_requires=">=2.7",
)
