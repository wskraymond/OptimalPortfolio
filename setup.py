import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="OptimalPortfolio",
    version="0.0.1",
    author="Author",
    author_email="author@example.com",
    description="Optimal Portfolio",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    project_urls={
        "Bug Tracker": "",
    },
    classifiers=[
        "Programming Language :: Python :: 3"
    ],
    install_requires=[
        'pandas',
        'numpy',
        'datetime',
        'pandas_datareader',
        'scipy',
        'matplotlib',
        'requests'
    ],
    packages=setuptools.find_packages(where="lib"),
    python_requires=">=3.6"
)
