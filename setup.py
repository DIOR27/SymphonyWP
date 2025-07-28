from setuptools import setup, find_packages

setup(
    name="SymphonyWP",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "typer[all]",
        "jinja2",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "symphony=symphony.cli:app"
        ]
    },
    include_package_data=True,
    package_data={
        "symphony": ["templates/**/*.j2", "locales/**/*.mo"],
    },
    author="TuNombre",
    description="CLI para gestión de instancias WordPress con Docker",
    classifiers=["Programming Language :: Python :: 3"],
)
