from __future__ import annotations
from dataclasses import dataclass, asdict
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional


ROOT = Path.cwd()



DEFAULTS = {
    'prometheus_image': 'prom/prometheus:latest',
    'grafana_image': 'grafana/grafana:latest',
    'node_exporter_image': 'prom/node-exporter:latest',
    'dcgm_exporter_image': 'nvidia/dcgm-exporter:latest',
    'prometheus_port': 9090,
    'grafana_port': 3000,
    'node_exporter_port': 9100,
    'dcgm_exporter_port': 9400,
    'grafana_admin_user': 'admin',
    'grafana_admin_password': 'admin',
}

@dataclass
class Node:
    name: str
    address: str  # hostname or IP reachable from the Prometheus server
    user: str = ""  # optional: ssh user for deploy helper
    gpu: bool = False


@dataclass
class Stack:
    server_host: str = "localhost"
    server_user: str = ""
    nodes: Optional[List[Node]] = None
    settings: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, str]:
        return {
            "server_host": self.server_host,
            "server_user": self.server_user,
            "nodes": [asdict(node) for node in (self.nodes or [])],
            "settings": self.settings or DEFAULTS,
        }

    @staticmethod
    def from_dict(d: Dict[str, str]) -> "Stack":
        nodes = [Node(**node) for node in d.get("nodes", [])]
        settings = d.get("settings", DEFAULTS.copy())
        merged = DEFAULTS.copy(); merged.update(settings)
        return Stack(
            server_host=d.get("server_host", "localhost"),
            server_user=d.get("server_user", ""),
            nodes=nodes,
            settings=merged,
        )

SERVER_COMPOSE_TPL = """
services:
    prometheus:
        image: ${prometheus_image}
        container_name: prometheus
        restart: unless-stopped
        ports:
            - "${prometheus_port}:9090"
        volumes:
            - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
            - ./prometheus/rules:/etc/prometheus/rules:ro
            - prometheus_data:/prometheus
        command:
            - '--config.file=/etc/prometheus/prometheus.yml'
            - '--storage.tsdb.path=/prometheus'
            - '--web.enable-lifecycle'
    grafana:
        image: ${grafana_image}
        container_name: grafana
        restart: unless-stopped
        ports:
            - "${grafana_port}:3000"
        volumes:
            - ./grafana/provisioning:/etc/grafana/provisioning
            - ./grafana/dashboards:/var/lib/grafana/dashboards
            - grafana_data:/var/lib/grafana
        environment:
            - GF_SECURITY_ADMIN_USER=${grafana_admin_user}
            - GF_SECURITY_ADMIN_PASSWORD=${grafana_admin_password}
            - GF_USERS_ALLOW_SIGN_UP=false
volumes:
    prometheus_data:
    grafana_data:
""".lstrip()

NODE_COMPOSE_TPL = """
services:
    node_exporter:
        image: ${node_exporter_image}
        container_name: node_exporter
        restart: unless-stopped
        command:
            - '--path.rootfs=/host'
        volumes:
            - /proc:/host/proc:ro
            - /sys:/host/sys:ro
            - /:/host:ro
        network_mode: host
        pid: host
        command:
            - --path.rootfs=/host
        volumes:
            - /:/host:ro,rslave
${gpu_block}
""".lstrip()

GPU_BLOCK_TPL = """
    dcgm_exporter:
        image: ${dcgm_exporter_image}
        container_name: dcgm_exporter
        restart: unless-stopped
        network_mode: host
        deploy:
            resources:
                reservations:
                    devices:
                        - capabilities: [gpu]
        environment:
            - DCGM_EXPORTER_LISTEN=${dcgm_exporter_port}
""".rstrip()

PROMETHEUS_YML_PREAMBLE = {
    'global': {
        'scrape_interval': '15s',
        'evaluation_interval': '15s',
    },
    'rule_files': ['/etc/prometheus/rules/*.yml'],
    'scrape_configs': []
}

GRAFANA_DATASOURCE_YML = {
    'apiVersion': 1,
    'datasources': [
        {
            'name': 'Prometheus',
            'type': 'prometheus',
            'access': 'proxy',
            'orgId': 1,
            'url': 'http://prometheus:9090',
            'isDefault': True,
            'jsonData': {'httpMethod': 'POST'},
            'version': 1,
            'editable': False,
        },
    ],
}

