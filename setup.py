#!/usr/bin/env python3
"""
Setup script pour le projet Wilderness-like.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="wilderness-prototype",
    version="0.1.0",
    author="Wilderness Team",
    description="Prototype de jeu exploration/survie avec génération procédurale et IA",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "black>=23.0.0",
            "flake8>=6.0.0", 
            "mypy>=1.6.0",
            "pre-commit>=3.5.0",
        ],
        "docs": [
            "sphinx>=7.1.0",
            "sphinx-rtd-theme>=1.3.0",
        ],
        "gpu": [
            "cupy-cuda11x>=12.0.0",
            "torch>=2.2.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "wilderness-heightmap=terrain_gen.heightmap:main",
        ],
    },
) 