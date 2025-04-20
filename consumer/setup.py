from setuptools import setup, find_packages

setup(
    name="consumer",
    version="1.0.0",
    packages=["consumer", "consumer.src", "consumer.src.utils"],
    package_dir={"consumer": "."},
    install_requires=[
        "confluent-kafka",
        "pymongo",
        "prometheus-client",
        "python-json-logger",
        "tenacity",
    ],
    entry_points={
        "console_scripts": [
            "kafka-consumer=consumer.src.consumer:main",
        ],
    },
    python_requires=">=3.8",
)
