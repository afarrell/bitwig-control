from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-bitwig",
    version="1.0.0",
    description="CLI harness for controlling Bitwig Studio via OSC (DrivenByMoss)",
    long_description=open("cli_anything/bitwig/README.md").read(),
    long_description_content_type="text/markdown",
    author="cli-anything",
    license="MIT",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
        "python-osc>=1.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cli-anything-bitwig=cli_anything.bitwig.bitwig_cli:main",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Multimedia :: Sound/Audio",
        "Environment :: Console",
    ],
)
