"""
Setup script for Betting AI System
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="betting-ai-system",
    version="1.0.0",
    author="Betting AI Team",
    author_email="support@bettingai.example.com",
    description="AI-powered betting analysis and recommendation system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/betting-ai-system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "betting-ai=src.cli.commands:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json"],
    },
)
