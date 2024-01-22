import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="aiosocketproto",
    version="0.0.11",
    author="Roman D.",
    description="A simple and universal socket protocol written in Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/webdenisenko/aiosocketproto",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10'
)
