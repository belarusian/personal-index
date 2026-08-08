from setuptools import setup, find_packages

setup(
    name="personal-index",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.8.0",
        "beautifulsoup4>=4.11.0",
        "aiofiles>=23.0.0",
        "click>=8.1.0",
    ],
    entry_points={
        "console_scripts": [
            "personal-index=personal_index.cli:cli",
        ],
    },
    python_requires=">=3.9",
)
