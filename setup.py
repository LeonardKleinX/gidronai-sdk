"""Setup configuration for gidronai-sdk."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="gidronai-sdk",
    version="0.3.0",
    author="Leonard Klein",
    author_email="leonard@gidronai.me",
    description="Official Python SDK for the GidronAI cloud API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/LeonardKleinX/gidronai-sdk",
    project_urls={
        "Documentation": "https://docs.gidronai.me/sdk",
        "Bug Tracker": "https://github.com/LeonardKleinX/gidronai-sdk/issues",
    },
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "httpx>=0.25",
        "pydantic>=2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "respx>=0.20",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
