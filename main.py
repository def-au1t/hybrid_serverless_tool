from config_manager import ConfigManager
from resource_provisioner import ResourceProvisioner
from time import sleep


def main():
    config_manager = ConfigManager("experiment.yml")

    cluster_instances = config_manager.get_cluster_instances()
    scenarios = config_manager.get_scenarios()


    provisioner = ResourceProvisioner(cluster_instances)

    # Create or update services in the clusters
    for scenario in scenarios:
        for stage in scenario['stages']:
            app_config = stage['app_config']
            for cluster_name in cluster_instances:
                provisioner.create_or_update_service(cluster_name, "default", app_config)

    # Use the `cluster_instances` and `scenarios` data for provisioning, testing, and metrics collection
    print(cluster_instances)
    print(scenarios)

    # sleep 20s
    sleep(20)

    for cluster_name in cluster_instances:
        provisioner.remove_service(cluster_name, "default", "cpu-1")


if __name__ == "__main__":
    main()

