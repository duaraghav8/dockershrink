from setuptools import setup, find_packages

from cli import VERSION

setup(
    name="dockershrink",
    version=VERSION,
    author="Raghav",
    author_email="dockershrink@gmail.com",
    description="Commandline tool to reduce the size of your Docker Images",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/duaraghav8/dockershrink",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "colorama>=0.4.6",
        "openai>=1.47.0",
        "setuptools>=75.2.0",
        "dockerfile>=3.3.1",
        "bashlex>=0.18",
    ],
    entry_points={
        "console_scripts": [
            "dockershrink=cli:main",
        ],
    },
    python_requires=">=3.6",
    include_package_data=True,
)
