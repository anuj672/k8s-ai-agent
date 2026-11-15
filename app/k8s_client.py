from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException

try:
    config.load_incluster_config()
except ConfigException:
    config.load_kube_config()

core = client.CoreV1Api()
apps = client.AppsV1Api()
discovery = client.DiscoveryV1Api()