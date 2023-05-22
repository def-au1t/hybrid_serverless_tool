from config_manager import ConfigManager
from resource_provisioner import ResourceProvisioner
from benchmarking_orchestrator import BenchmarkingOrchestrator
import time


def main():
    config_manager = ConfigManager(config_path="experiment.yml")

    resource_provisioner = ResourceProvisioner(config_manager)
    benchmark_orchestrator = BenchmarkingOrchestrator(
        config_manager, resource_provisioner)

    benchmark_orchestrator.run_benchmark("scenario-1")


if __name__ == "__main__":
    main()
