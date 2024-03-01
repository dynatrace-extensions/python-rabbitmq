from setuptools import setup, find_packages

# get version from extension/extension.yaml
# note, we can't parse yaml
with open("extension/extension.yaml") as f:
    for line in f:
        if "version" in line:
            version = line.split(":")[1].strip()
            break

setup(name="rabbitmq_extension",
      version=version,
      description="rabbitmq_extension for Extension 2.0",
      author="Dynatrace",
      packages=find_packages(),
      python_requires=">=3.10",
      include_package_data=True,
      install_requires=["dt-extensions-sdk", "requests"],
      extras_require={"dev": ["dt-extensions-sdk[cli]"]},
      )
