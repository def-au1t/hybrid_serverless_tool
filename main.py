from config_manager import ConfigManager
from data_aggregator import DataAggregator
from resource_provisioner import ResourceProvisioner
from benchmarking_orchestrator import BenchmarkingOrchestrator
from metrics_collector import MetricsCollector

from visualizer import Visualizer


experiments = ["1_centralized"]


def main():
    config_manager = ConfigManager(config_path="experiment.yml")

    resource_provisioner = ResourceProvisioner(config_manager)
    benchmark_orchestrator = BenchmarkingOrchestrator(
        config_manager, resource_provisioner)

    for experiment in experiments:
        benchmark_orchestrator.run_benchmark(experiment)

        aggregator = DataAggregator(experiment)
        print(aggregator.results_df)
        visualizer = Visualizer(aggregator)
        visualizer.visualize()


if __name__ == "__main__":
    main()
