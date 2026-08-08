from setuptools import setup, find_packages

setup(
    name="personal-index",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.9.0",
        "beautifulsoup4>=4.12.0",
        "aiosqlite>=0.19.0",
        "schedule>=1.2.0",
        "click>=8.1.0",
        "rich>=13.6.0",
        "python-dateutil>=2.8.0",
    ],
    entry_points={
        "console_scripts": [
            "personal-index=personal_index.cli:main",
        ],
    },
)
