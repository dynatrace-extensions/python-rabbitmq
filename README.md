# RabbitMQ Management API Extension

This is an example of a real extension to monitor RabbitMQ

## Getting started

### Run a local RabbitMQ instance

```bash
docker run -d --name rabbit -p 15672:15672 rabbitmq:3-management
```

### Install the dependencies

```bash
pip install dt-extensions-sdk[cli] requests
```

### Run the extension

```bash
dt-sdk run
```
