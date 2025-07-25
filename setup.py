# setup.py
import io

from setuptools import find_packages, setup

with io.open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="guardbot",
    version="0.1.0",
    description="Slack bot for tracking user points",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Shreeram Modi",
    author_email="smodi@smodi.net",
    url="https://github.com/shrimpram/guardbot",
    packages=find_packages(where="."),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "Flask>=2.0.0",
        "slack-sdk>=3.0.0",
        "slackeventsapi>=2.0.0",
        "python-dotenv>=0.20.0",
        "datetime>=5.5",
    ],
    entry_points={
        "console_scripts": [
            "init-students = app.init_students:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.13",
        "Framework :: Flask",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
