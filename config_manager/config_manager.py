import yaml
from kubernetes import client, config
import os


class ConfigManager:
    def __init__(self, config_path=None):
        self.config_path = config_path
        self.clusters = {}
        self.apps = {}
        self.scenarios = []
        self.api_clients = {}
        self.base_path = os.path.dirname(os.path.abspath(config_path))
        self.load_config()

    def load_kube_config(self, cluster_config, force_reload=False):
        cluster_name = cluster_config['name']
        if not force_reload and cluster_name in self.api_clients:
            return self.api_clients[cluster_name]

        kubeconfig_path = os.path.join(
            self.base_path, 'config', cluster_config['kubeconfig'])
        config.load_kube_config(config_file=kubeconfig_path)
        api_client = client.ApiClient()

        self.api_clients[cluster_name] = api_client
        return api_client

    def load_config(self):
        with open(self.config_path, 'r') as f:
            configs = yaml.safe_load(f)

        self.clusters = configs['clusters']
        self.apps = configs['apps']
        self.scenarios = configs['scenarios']

    def get_cluster_by_name(self, cluster_name):
        return next((c for c in self.clusters if c['name'] == cluster_name), None)

    def get_app_by_name(self, app_name):
        return next((a for a in self.apps if a['name'] == app_name), None)

    def get_scenario_by_name(self, scenario_name):
        return next((s for s in self.scenarios if s['name'] == scenario_name), None)
