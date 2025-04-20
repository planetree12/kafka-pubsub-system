from setuptools import setup, find_packages

setup(
    name="producer",
    version="0.1.0",
    packages=["producer", "producer.src", "producer.src.utils"],
    package_dir={"producer": "."},
    install_requires=[
        "kafka-python",
        "retry",
        "jsonschema",
        "structlog",
    ],
    python_requires=">=3.6",
)
