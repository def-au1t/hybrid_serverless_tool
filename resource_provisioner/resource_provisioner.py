from kubernetes import client


class ResourceProvisioner:
    def __init__(self, config_manager):
        self.config_manager = config_manager

    def deploy_knative_service(self, app_config, api_client):
        env_vars = [client.V1EnvVar(
            name=var['name'], value=var['value']) for var in app_config['env']]

        container = client.V1Container(name=app_config['name'],
                                       image=app_config['image'],
                                       env=env_vars,
                                       resources=client.V1ResourceRequirements(limits=app_config['resource_limits']))

        revision_name = f"{app_config['name']}-revision"

        knative_annotation_prefix = "autoscaling.knative.dev"
        annotations = {
            f"{knative_annotation_prefix}/minScale": str(app_config['knative_limits']['min_scale']),
            f"{knative_annotation_prefix}/maxScale": str(app_config['knative_limits']['max_scale']),
            f"{knative_annotation_prefix}/target": str(app_config['knative_limits']['target_concurrency']),
            f"{knative_annotation_prefix}/metric": "concurrency"}

        knative_service = {
            "apiVersion": "serving.knative.dev/v1",
            "kind": "Service",
            "metadata": {
                "name": app_config['name'],
                "namespace": "default",
                "labels": {"serving.knative.dev/visibility": "cluster-local"}
            },
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": annotations,
                        "labels":  {
                            "app": app_config['name'],
                            "serving.knative.dev/visibility": "cluster-local"
                        }
                    },
                    "spec": {
                        "containers": [container]
                    }
                }
            }
        }

        custom_objects_api = client.CustomObjectsApi(api_client=api_client)
        custom_objects_api = client.CustomObjectsApi(api_client=api_client)

        try:
            # Try getting the existing service
            service = custom_objects_api.get_namespaced_custom_object(group="serving.knative.dev",
                                                                      version="v1",
                                                                      namespace="default",
                                                                      plural="services",
                                                                      name=app_config['name'])

            custom_objects_api.patch_namespaced_custom_object(group="serving.knative.dev",
                                                              version="v1",
                                                              namespace="default",
                                                              plural="services",
                                                              name=app_config['name'],
                                                              body=knative_service)

        except client.exceptions.ApiException as e:
            if e.status == 404:  # If service not found, create a new one
                custom_objects_api.create_namespaced_custom_object(group="serving.knative.dev",
                                                                   version="v1",
                                                                   namespace="default",
                                                                   plural="services",
                                                                   body=knative_service)
            else:
                raise e

    def delete_knative_service(self, app_name, api_client):
        custom_objects_api = client.CustomObjectsApi(api_client=api_client)

        try:
            # Attempt to delete the Knative service
            custom_objects_api.delete_namespaced_custom_object(group="serving.knative.dev",
                                                               version="v1",
                                                               namespace="default",
                                                               plural="services",
                                                               name=app_name)
        except client.exceptions.ApiException as e:
            if e.status != 404:  # If the error is anything other than "NotFound", raise the error
                raise e
            else:
                print(f"Service '{app_name}' not found. Skipping deletion.")

    def _remove_unused_services(self, app_names_to_keep, api_client):
        custom_objects_api = client.CustomObjectsApi(api_client=api_client)
        service_list = custom_objects_api.list_namespaced_custom_object(group="serving.knative.dev",
                                                                        version="v1",
                                                                        namespace="default",
                                                                        plural="services")

        for service in service_list['items']:
            service_name = service['metadata']['name']
            if service_name not in app_names_to_keep:
                self.delete_knative_service(service_name, api_client)

    def _should_remove_service(self, service, next_created_services):
        return (
            any(svc['name'] == service['name'] and svc['api_client'] !=
                service['api_client'] for svc in next_created_services)
            or service['name'] not in [svc['name'] for svc in next_created_services]
        )

    def deploy_scenario(self, scenario):
        all_created_services = []
        previous_created_services = []

        # Iterate through each stage in the scenario
        for stage_idx, stage in enumerate(scenario['stages']):
            created_services = []

            # Iterate through each app in the stage
            for app_config_overrides in stage['apps']:
                app_name = app_config_overrides['name']
                # Use a copy to avoid modifying the original config
                app_config = self.config_manager.get_app_by_name(
                    app_name).copy()
                app_config.update(app_config_overrides)

                cluster_config = self.config_manager.get_cluster_by_name(
                    app_config['cluster'])
                api_client = self.config_manager.load_kube_config(
                    cluster_config)  # Get the API client for the targeted cluster

                # Deploy or update the Knative service
                self.deploy_knative_service(app_config, api_client)
                created_services.append(
                    {"name": app_name, "api_client": api_client})
                all_created_services.append(
                    {"name": app_name, "api_client": api_client})

            # Remove unused services from previous stage
            for service in previous_created_services:
                if self._should_remove_service(service, created_services):
                    print("Removing unused service", service["name"])
                    self.delete_knative_service(
                        service["name"], service["api_client"])

            # Save created services for next round
            previous_created_services = created_services.copy()
            # Yield the current stage so the caller can do something (benchmarking, collecting metrics, ...)
            yield stage

        # Cleanup
        for svc in all_created_services:
            self.delete_knative_service(svc["name"], svc["api_client"])
