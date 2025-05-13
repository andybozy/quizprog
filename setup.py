from setuptools import setup, find_packages

setup(
    name="quizprog",
    version="2.6.3",
    packages=find_packages(include=["quizlib", "quizlib.*"]),
    entry_points={
        "console_scripts": [
            "quizprog=quizlib.main:main"
        ]
    }
)
