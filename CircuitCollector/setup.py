from setuptools import setup, find_packages

setup(
    name="CircuitCollector",
    version="0.1",
    # auto find modules
    packages=find_packages(),
    install_requires=[
        "jinja2",
        "toml",
        "numpy",
        "fastapi",
        "pydantic",
        "redis",
    ],
    python_requires=">=3.11",
    author="Jiyuan",
    description="Analog circuit testbench generator and simulation framework.",
)
