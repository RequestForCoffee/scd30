import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="scd30_i2c",
    version="0.0.1",
    author="RequestForCoffee",
    author_email="requestforcoffee@example.com",
    description="Sensirion ",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/RequestForCoffee/scd30",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=3.7.3',
)