from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

with open("requirements-dev.txt", "r", encoding="utf-8") as fh:
    dev_requirements = [
        line.strip()
        for line in fh
        if line.strip() and not line.startswith("#") and not line.startswith("-r")
    ]

setup(
    name="aquant-agent",
    version="0.1.0",
    author="AQuant-Agent",
    author_email="aquant-agent@proton.me",
    description="A股量化智能体 - 10个AI分析师协同决策",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cliu-debug/astock-agents",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Developers",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: Free For Educational Use",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
    },
    entry_points={
        "console_scripts": [
            "aquant-agent=astock_agents.cli:main",
        ],
    },
)
