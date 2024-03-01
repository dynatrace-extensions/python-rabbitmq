from typing import List
import logging

import requests

default_logger = logging.getLogger(__name__)
default_logger.setLevel(logging.INFO)
PAGE_SIZE = 100


class Queue:
    def __init__(self, raw_json: dict):

        self.name = raw_json.get('name')
        self.node = raw_json.get('node')
        self.state = raw_json.get('state')
        self.vhost = raw_json.get('vhost', "/")
        self.durable = raw_json.get('durable', False)
        self.policy = raw_json.get('policy', None)
        self.type = raw_json.get('type', 'classic')

        self.messages = raw_json.get('messages', 0)
        self.messages_ready = raw_json.get('messages_ready', 0)
        self.messages_unacknowledged = raw_json.get('messages_unacknowledged', 0)
        self.message_bytes = raw_json.get('message_bytes', 0)

        self.consumers = raw_json.get('consumers', 0)
        self.memory = raw_json.get('memory', 0)

        message_stats = raw_json.get('message_stats', {})
        self.messages_publish = message_stats.get('publish', 0)
        self.messages_deliver_no_ack = message_stats.get('deliver_no_ack', 0)
        self.messages_redeliver = message_stats.get('redeliver', 0)
        self.messages_return = message_stats.get('return', 0)
        self.messages_deliver_get = message_stats.get('deliver_get', 0)
        self.messages_return = message_stats.get('return_unroutable', 0)
        self.messages_ack = message_stats.get('ack', 0)
        self.drop_unroutable = message_stats.get('drop_unroutable', 0)
        self.return_unroutable = message_stats.get('return_unroutable', 0)

        # print(pprint.pformat(raw_json))

    def __repr__(self):
        return f'Queue({self.name}@{self.node})'


class Node:
    def __init__(self, raw_json: dict):

        self.partitions = len(raw_json.get('partitions', []))
        self.name = raw_json.get('name')
        self.type = raw_json.get('type')
        self.running = raw_json.get('running', False)
        self.processors = raw_json.get('processors', 0)

        self.uptime = raw_json.get('uptime', 0)
        self.mem_used = raw_json.get('mem_used', 0)
        self.mem_limit = raw_json.get('mem_limit', 1)
        self.mem_used_pct = self.mem_used / self.mem_limit * 100

        self.fd_used = raw_json.get('fd_used', 0)
        self.fd_total = raw_json.get('fd_total', 1)
        self.fd_used_pct = self.fd_used / self.fd_total * 100

        self.sockets_used = raw_json.get('sockets_used', 0)
        self.sockets_total = raw_json.get('sockets_total', 1)
        self.sockets_used_pct = self.sockets_used / self.sockets_total * 100

        self.proc_used = raw_json.get('proc_used', 0)
        self.proc_total = raw_json.get('proc_total', 1)
        self.proc_used_pct = self.proc_used / self.proc_total * 100

        self.disk_free = raw_json.get('disk_free', 0)

        self.gc_num = raw_json.get('gc_num', 0)
        self.ip = None

    def __repr__(self):
        return f'Node({self.name})'


class Connection:
    def __init__(self, raw_json: dict):
        self.name = raw_json.get('name')
        self.state = raw_json.get('state')  # running, blocked
        self.node = raw_json.get('node')

    def __repr__(self):
        return f'Connection({self.name})'


class Channel:
    def __init__(self, raw_json: dict):
        self.name = raw_json.get('name')
        self.state = raw_json.get('state')  # flow
        self.node = raw_json.get('node')

    def __repr__(self):
        return f'Channel({self.name})'


class Exchange:
    def __init__(self, raw_json: dict):
        self.name = raw_json.get('name')
        self.type = raw_json.get('type')

    def __repr__(self):
        return f'Exchange({self.name} - {self.type})'


class Consumer:
    def __init__(self, raw_json: dict):
        self.consumer_tag = raw_json.get('consumer_tag')

    def __repr__(self):
        return f'Consumer({self.consumer_tag})'


class Listener:
    def __init__(self, raw_json: dict):
        self.node = raw_json.get("node")
        self.protocol = raw_json.get("protocol")
        self.ip_address = raw_json.get("ip_address")
        self.port = raw_json.get("port")

    def __repr__(self):
        return f'Listener({self.node}:{self.port} ({self.protocol}))'


class Cluster:
    def __init__(self, raw_json: dict):
        self.name = raw_json.get('cluster_name')
        self.node = raw_json.get('node')
        self.rabbitmq_version = raw_json.get('rabbitmq_version')
        self.erlang_version = raw_json.get('erlang_version')

        # queue_totals
        queue_totals = raw_json.get('queue_totals', {})
        self.messages = queue_totals.get('messages', 0)
        self.messages_ready = queue_totals.get('messages_ready', 0)
        self.messages_unacknowledged = queue_totals.get('messages_unacknowledged', 0)

        self.listeners: List[Listener] = [Listener(listener) for listener in raw_json.get("listeners", [])]

        # object_totals
        object_totals = raw_json.get('object_totals', {})
        self.consumers = object_totals.get('consumers', 0)
        self.connections = object_totals.get('connections', 0)
        self.queues = object_totals.get('queues', 0)
        self.exchanges = object_totals.get('exchanges', 0)
        self.channels = object_totals.get('channels', 0)

        # message_stats
        message_stats = raw_json.get('message_stats', {})
        self.ack = message_stats.get('ack', 0)
        self.unack = message_stats.get('deliver_no_ack', 0)
        self.deliver_get = message_stats.get('deliver_get', 0)
        self.publish = message_stats.get('publish', 0)
        self.redeliver = message_stats.get('redeliver', 0)
        self.return_unroutable = message_stats.get('return_unroutable', 0)

    def __repr__(self):
        return f'Cluster({self.name}) - v{self.rabbitmq_version}'


class VirtualHost:
    def __init__(self, raw_json: dict):
        self.name = raw_json.get("name")
        self.messages = raw_json.get("messages", 0)
        self.messages_ready = raw_json.get("messages_ready", 0)
        self.messages_unacknowledged = raw_json.get("messages_unacknowledged", 0)
        self.recv_oct = raw_json.get("recv_oct", 0)
        self.send_oct = raw_json.get("send_oct", 0)
        self.description = raw_json.get("description")

    def __repr__(self):
        return f'VirtualHost({self.name}) - {self.messages}'


class RabbitMQClient:

    def __init__(self, address: str, username: str, password: str, logger=default_logger, page_size=PAGE_SIZE):
        self.logger = logger
        self.auth = (username, password)
        self.page_size = page_size

        self.base_url = address.rstrip("/")

    def make_request(self, url, method='GET', parameters=None):
        self.logger.info(f'RabbitMQClient - Calling "{url}" with parameters {parameters}')
        r = requests.request(method, url, auth=self.auth, timeout=30, params=parameters)
        if r.status_code >= 300:
            message = f'RabbitMQClient - Got {r} while calling "{url}"'
            self.logger.error(f'RabbitMQClient - Got {r} while calling "{url}"')
            raise Exception(message)
        else:
            return r.json()

    @property
    def virtual_hosts(self) -> List[VirtualHost]:
        url = f'{self.base_url}/api/vhosts'
        return [VirtualHost(raw_json) for raw_json in self.make_request(url)]

    @property
    def queues(self) -> List[Queue]:
        # TODO - Can we make pagination generic?

        url = f'{self.base_url}/api/queues'
        page_number = 1
        while True:
            parameters = {"page_size": self.page_size, "page": page_number}
            raw_json = self.make_request(url, parameters=parameters)
            page_count = raw_json.get("page_count", 0)
            page_number += 1
            for queue in raw_json.get("items", []):
                yield Queue(queue)

            if page_number > page_count:
                break

    @property
    def nodes(self) -> List[Node]:
        url = f'{self.base_url}/api/nodes'
        return [Node(raw_json) for raw_json in self.make_request(url)]

    @property
    def connections(self):
        url = f'{self.base_url}/api/connections'
        return [Connection(raw_json) for raw_json in self.make_request(url, parameters={"page_size": 1000})]

    # @property
    # def node_status(self):
    #     url = f'{self.base_url}/api/healthchecks/node'
    #     return self.make_request(url).get('status', None)

    @property
    def channels(self):
        url = f'{self.base_url}/api/channels'
        return [Channel(raw_json) for raw_json in self.make_request(url, parameters={"page_size": 1000})]

    @property
    def consumers(self):
        url = f'{self.base_url}/api/consumers'
        return [Consumer(raw_json) for raw_json in self.make_request(url)]

    @property
    def exchanges(self):
        url = f'{self.base_url}/api/exchanges'
        return [Exchange(raw_json) for raw_json in self.make_request(url, parameters={"page_size": 1000})]

    @property
    def cluster(self):
        url = f'{self.base_url}/api/overview'
        return Cluster(self.make_request(url))






