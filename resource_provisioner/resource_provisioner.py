from kubernetes import client


class ResourceProvisioner:
    def __init__(self, cluster_instances):
        self.cluster_instances = {}
        for cluster_name, core_api in cluster_instances.items():
            conf = core_api.api_client.configuration
            self.cluster_instances[cluster_name] = {
                'core_api': core_api,
                'custom_objects_api': client.CustomObjectsApi(client.ApiClient(conf))
            }

    def _create_knative_service(self, api, namespace, app_config):
        group = "serving.knative.dev"
        version = "v1"
        plural = "services"

        service = {
            "apiVersion": f"{group}/{version}",
            "kind": "Service",
            "metadata": {
                "name": app_config['name'],
                "namespace": namespace,
                "labels": {"serving.knative.dev/visibility": "cluster-local"}
            },
            "spec": {
                "template": {
                    "metadata": {
                        "labels": {"serving.knative.dev/visibility": "cluster-local"}
                    },
                    "spec": {
                        "containers": [
                            {
                                "image": app_config['app_image'],
                                "resources": app_config['resource_limits'],
                                "env": app_config['env']
                            }
                        ]
                    }
                },
            }
        }
        
        # Add knative_limits to the spec dictionary
        service['spec'].update(app_config['knative_limits'])

        try:
            api_response = api.create_namespaced_custom_object(group, version, namespace, plural, service, field_manager="knative_tool")
            print(f"Knative Service '{app_config['name']}' created in namespace '{namespace}'")
        except client.ApiException as e:
            print(f"Exception when calling CustomObjectsApi->create_namespaced_custom_object: {e}")


    def _update_knative_service(self, api, namespace, app_config):
        group = "serving.knative.dev"
        version = "v1"
        name = app_config['name']
        plural = "services"

        svc = api.get_namespaced_custom_object(group, version, namespace, plural, name)
        svc['spec'].update(app_config['knative_limits'])

        return api.patch_namespaced_custom_object(group, version, namespace, plural, name, svc, field_manager="knative_tool")

    def create_or_update_service(self, cluster_name, namespace, app_config):
        api = self.cluster_instances[cluster_name]['custom_objects_api']
        group = "serving.knative.dev"
        version = "v1"
        plural = "services"
        name = app_config['name']

        try:
            api.get_namespaced_custom_object(group, version, namespace, plural, name)
            print(f"Knative Service '{name}' exists, updating...")
            self._update_knative_service(api, namespace, app_config)
        except client.ApiException as e:
            if e.status == 404:
                print(f"Knative Service '{name}' not found, creating...")
                self._create_knative_service(api, namespace, app_config)
            else:
                raise e

        print(f"Knative Service '{name}' is successfully created or updated in namespace '{namespace}' on cluster '{cluster_name}'.")

    def remove_service(self, cluster_name, namespace, service_name):
        api = self.cluster_instances[cluster_name]['custom_objects_api']
        group = "serving.knative.dev"
        version = "v1"
        plural = "services"

        try:
            api.delete_namespaced_custom_object(group, version, namespace, plural, service_name)
            print(f"Knative Service '{service_name}' successfully removed from namespace '{namespace}' on cluster '{cluster_name}'.")
        except client.ApiException as e:
            if e.status == 404:
                print(f"Knative Service '{service_name}' not found in namespace '{namespace}'.")
            else:
                raise e