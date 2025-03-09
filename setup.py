from setuptools import setup, find_packages

setup(
    name="quizprog",
    version="0.1.0",
    packages=find_packages(include=["quizlib", "quizlib.*"]),
    entry_points={
        "console_scripts": [
            "quizprog=main:main"
        ]
    }
)
