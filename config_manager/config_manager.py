import yaml
import os
from kubernetes import client, config as kube_config


class ConfigManager:
    def __init__(self, config_file):
        self.config_file = config_file

        with open(self.config_file, 'r') as file:
            self.config_data = yaml.safe_load(file)

        self.default = self.config_data.get('default', {})
        self.clusters = self.config_data['clusters']
        self.scenarios = self.config_data['scenarios']        
        self.base_path = os.path.dirname(os.path.abspath(config_file))


    def _apply_defaults(self, specific_config):
        combined_config = self.default.copy()
        combined_config.update(specific_config)
        return combined_config

    def get_cluster_instances(self):
        cluster_instances = {}
        for cluster in self.clusters:
            name = cluster['name']
            kubeconfig_path = os.path.join(self.base_path, 'config', cluster['kubeconfig'])

            if not os.path.exists(kubeconfig_path):
                raise FileNotFoundError(f"Kubeconfig not found at {kubeconfig_path}")

            kube_config.load_kube_config(kubeconfig_path)
            api_instance = client.CoreV1Api()
            cluster_instances[name] = api_instance

        return cluster_instances

    def get_scenarios(self):
        scenarios_data = []
        for scenario in self.scenarios:
            scenario_name = scenario['name']
            scenario_stages = []

            for stage in scenario['stages']:
                app_config = stage['app_config']
                updated_app_config = self._apply_defaults(app_config)
                stage_config = {
                    'name': stage['name'],
                    'duration': stage['duration'],
                    'app_config': updated_app_config,
                }
                scenario_stages.append(stage_config)

            scenarios_data.append({
                'name': scenario_name,
                'stages': scenario_stages,
            })

        return scenarios_data
