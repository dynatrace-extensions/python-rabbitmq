import re
import socket
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List
from datetime import timedelta, datetime
from urllib.parse import urlparse

from dynatrace_extension import Extension, MetricType
from dynatrace_extension.sdk.communication import Status, StatusValue

from .rabbitmq_api import RabbitMQClient


class RabbitMQExtension(Extension):

    def __init__(self):
        self.extension_name = "rabbitmq_extension"
        self.executor = ThreadPoolExecutor(max_workers=10)
        super().__init__()

    def initialize(self, **kwargs):

        endpoints = self.activation_config.get("endpoints")
        for endpoint in endpoints:
            frequency = endpoint.get("frequency", 1)

            # Schedule the monitor method to be run every <frequency> minutes
            # We also pass the endpoint as a parameter to this method
            self.schedule(self.monitor, timedelta(minutes=frequency), (endpoint,))

    def create_rabbitmq_client(self, endpoint: Dict) -> RabbitMQClient:
        username = endpoint.get("user", "guest")
        password = endpoint.get("password", "guest")
        for node in endpoint["nodes"]:
            rabbit = RabbitMQClient(node, username, password, logger=self.logger)
            try:
                _ = rabbit.cluster
                self.logger.info(f"Successfully connected to {rabbit.base_url}")
                return rabbit
            except Exception as e:
                self.logger.warning(f"Could not connect to RabbitMQ node {rabbit.base_url}: {repr(e)}")
        raise Exception(f"Could not connect to any of the nodes in {endpoint['nodes']}")

    def fastcheck(self) -> Status:
        for endpoint in self.activation_config.get("endpoints"):
            rabbit = self.create_rabbitmq_client(endpoint)
            try:
                _ = rabbit.cluster
                self.logger.info(f"Successfully connected to {rabbit.base_url}")
            except Exception as e:
                error_message = f"Could not connect to RabbitMQ node {rabbit.base_url}: {repr(e)}"
                self.logger.error(error_message)
                return Status(StatusValue.DEVICE_CONNECTION_ERROR, error_message)

        return Status(StatusValue.OK, "This AG can monitor RabbitMQ")

    def monitor(self, endpoint: Dict):
        rabbit = self.create_rabbitmq_client(endpoint)
        cluster_name = endpoint.get("cluster_name", "rabbitmq")

        # parse the DNS name out of the URL
        dns_name = urlparse(rabbit.base_url).netloc.split(":")[0]

        # We always collect metrics for the cluster
        cluster = rabbit.cluster
        cluster_dimensions = {
            "cluster": cluster_name,
            "node": cluster.node,
            "rabbitmq_version": cluster.rabbitmq_version,
            "erlang_version": cluster.erlang_version,
            "dt.dns_names": dns_name,
        }

        # Try to extract the IP address
        try:
            ip_address = socket.gethostbyname(dns_name)
            cluster_dimensions["dt.ip_addresses"] = ip_address
        except Exception as e:
            self.logger.warning(f"Could not resolve {dns_name}: {repr(e)}")

        # Extract the different ports, we only care about the AMQP ones
        amqp_listeners = [listener for listener in cluster.listeners if "amqp" in listener.protocol]
        if amqp_listeners:
            cluster_dimensions["dt.listen_ports"] = ",".join([f"{listener.port}" for listener in amqp_listeners])

        self.logger.info(f"collected cluster level dimensions: {cluster_dimensions}")
        self.logger.info(f"enabled feature sets: {self.enabled_feature_sets_names}")

        if "Cluster" in self.enabled_feature_sets_names:

            self.report_metric("rabbitmq.cluster.messages", cluster.messages_ready, cluster_dimensions)
            self.report_metric("rabbitmq.cluster.messages_ready", cluster.messages_ready, cluster_dimensions)
            self.report_metric("rabbitmq.cluster.messages_unacknowledged", cluster.messages_unacknowledged, cluster_dimensions)
            self.report_metric("rabbitmq.cluster.consumers", cluster.consumers, cluster_dimensions)
            self.report_metric("rabbitmq.cluster.connections", cluster.connections, cluster_dimensions)
            self.report_metric("rabbitmq.cluster.queues", cluster.queues, cluster_dimensions)
            self.report_metric("rabbitmq.cluster.exchanges", cluster.exchanges, cluster_dimensions)
            self.report_metric("rabbitmq.cluster.channels", cluster.channels, cluster_dimensions)

            # deltas
            self.report_metric("rabbitmq.cluster.ack.count", cluster.ack, cluster_dimensions, metric_type=MetricType.COUNT, timestamp=datetime.now())
            self.report_metric("rabbitmq.cluster.unack.count", cluster.unack, cluster_dimensions, metric_type=MetricType.COUNT, timestamp=datetime.now())
            self.report_metric("rabbitmq.cluster.deliver_get.count", cluster.deliver_get, cluster_dimensions, metric_type=MetricType.COUNT, timestamp=datetime.now())
            self.report_metric("rabbitmq.cluster.publish.count", cluster.publish, cluster_dimensions, metric_type=MetricType.COUNT, timestamp=datetime.now())

        if "Queue" in self.enabled_feature_sets_names:
            self.executor.submit(self.collect_queues, rabbit, endpoint, cluster_dimensions)

        if "Node" in self.enabled_feature_sets_names:
            self.executor.submit(self.collect_nodes, rabbit, cluster_dimensions)

        if "Virtual Host" in self.enabled_feature_sets_names:
            self.executor.submit(self.collect_vhosts, rabbit, cluster_dimensions)

    def collect_queues(self, rabbit: RabbitMQClient, endpoint: Dict, parent_dimensions: Dict):
        try:
            # Labels: cluster, vhost, queue, durable, policy
            queues_to_monitor = endpoint.get("queues_include", [".*"])
            for queue in rabbit.queues:
                if not self.should_monitor_queue(queue.name, queues_to_monitor):
                    continue

                queue_dimensions = {
                    **parent_dimensions,
                    "vhost": queue.vhost,
                    "queue": queue.name,
                    "node": queue.node,
                    "durable": f"{queue.durable}",
                    "policy": f"{queue.policy}",
                    "state": queue.state,
                    "type": queue.type
                }
                # report queue metrics
                self.report_metric("rabbitmq.queue.messages", queue.messages, queue_dimensions)
                self.report_metric("rabbitmq.queue.messages_ready", queue.messages_ready, queue_dimensions)
                self.report_metric("rabbitmq.queue.messages_unacknowledged", queue.messages_unacknowledged, queue_dimensions)
                self.report_metric("rabbitmq.queue.message_bytes", queue.message_bytes, queue_dimensions)
                self.report_metric("rabbitmq.queue.memory", queue.memory, queue_dimensions)
                self.report_metric("rabbitmq.queue.consumers", queue.consumers, queue_dimensions)

                # deltas
                self.report_metric("rabbitmq.queue.publish.count", queue.messages_publish, queue_dimensions, metric_type=MetricType.COUNT, timestamp=datetime.now())
                self.report_metric("rabbitmq.queue.redeliver.count", queue.messages_redeliver, queue_dimensions, metric_type=MetricType.COUNT, timestamp=datetime.now())
                self.report_metric("rabbitmq.queue.messages_delivered.count", queue.messages_deliver_get, queue_dimensions, metric_type=MetricType.COUNT, timestamp=datetime.now())
                self.report_metric("rabbitmq.queue.messages_deliver_no_ack.count", queue.messages_deliver_no_ack, queue_dimensions, metric_type=MetricType.COUNT, timestamp=datetime.now())
                self.report_metric("rabbitmq.queue.drop_unroutable.count", queue.drop_unroutable, queue_dimensions, metric_type=MetricType.COUNT, timestamp=datetime.now())
                self.report_metric("rabbitmq.queue.return_unroutable.count", queue.return_unroutable, queue_dimensions, metric_type=MetricType.COUNT, timestamp=datetime.now())
        except Exception as e:
            self.logger.exception(f"Could not collect queues: {repr(e)}")

    def collect_nodes(self, rabbit: RabbitMQClient,  parent_dimensions: Dict):
        try:

            for node in rabbit.nodes:
                node_dimensions = {
                    **parent_dimensions,
                    "node": node.name,
                    "type": node.type,
                    "running": f"{node.running}",
                    "processors": node.processors,
                }

                self.report_metric("rabbitmq.node.mem_used", node.mem_used, node_dimensions)
                self.report_metric("rabbitmq.node.mem_limit", node.mem_limit, node_dimensions)
                self.report_metric("rabbitmq.node.fd_used", node.fd_used, node_dimensions)
                self.report_metric("rabbitmq.node.fd_total", node.fd_total, node_dimensions)
                self.report_metric("rabbitmq.node.sockets_used", node.sockets_used, node_dimensions)
                self.report_metric("rabbitmq.node.sockets_total", node.sockets_total, node_dimensions)
                self.report_metric("rabbitmq.node.disk_free", node.disk_free, node_dimensions)
                self.report_metric("rabbitmq.node.partitions", node.partitions, node_dimensions)
                self.report_metric("rabbitmq.node.uptime", node.uptime, node_dimensions)

                # deltas
                self.report_metric("rabbitmq.node.gc_num.count", node.gc_num, node_dimensions, metric_type=MetricType.COUNT, timestamp=datetime.now())
        except Exception as e:
            self.logger.exception(f"Could not collect nodes: {repr(e)}")

    def collect_vhosts(self, rabbit: RabbitMQClient, parent_dimensions: Dict):
        try:
            for vhost in rabbit.virtual_hosts:
                vhost_dimensions = {
                    **parent_dimensions,
                    "vhost": vhost.name,
                    "description": vhost.description,
                }
                self.report_metric("rabbitmq.vhost.messages", vhost.messages, vhost_dimensions)
                self.report_metric("rabbitmq.vhost.messages_ready", vhost.messages_ready, vhost_dimensions)
                self.report_metric("rabbitmq.vhost.messages_unacknowledged", vhost.messages_unacknowledged, vhost_dimensions)

                # deltas
                self.report_metric("rabbitmq.vhost.recv_oct.count", vhost.recv_oct, vhost_dimensions, metric_type=MetricType.COUNT, timestamp=datetime.now())
                self.report_metric("rabbitmq.vhost.send_oct.count", vhost.send_oct, vhost_dimensions, metric_type=MetricType.COUNT, timestamp=datetime.now())

        except Exception as e:
            self.logger.exception(f"Could not collect vhosts: {repr(e)}")

    @staticmethod
    def should_monitor_queue(queue_name: str, queues_to_monitor: List[str]) -> bool:
        for queue_regex in queues_to_monitor:
            if re.match(queue_regex, queue_name):
                return True
        return False


def main():
    RabbitMQExtension().run()


if __name__ == '__main__':
    main()
