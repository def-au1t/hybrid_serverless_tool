import csv
import os
from datetime import datetime
from kubernetes import client
from prometheus_api_client import PrometheusConnect


class MetricsCollector:
    def __init__(self, config_manager):
        self.config_manager = config_manager

    def _save_metrics_to_csv(self, metrics, output_file, cluster_name, stage_name):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            for metric in metrics:
                writer.writerow(
                    [metric["timestamp"], cluster_name, stage_name, metric["name"], metric["value"], metric["metric"]])

    def collect_knative_metrics(self, prometheus_url, metrics, start_time, end_time):
        prometheus = PrometheusConnect(url=prometheus_url, disable_ssl=True)

        result = {}
        for metric in metrics:
            data = prometheus.custom_query_range(
                query=metric["query"], start_time=start_time, end_time=end_time, step="5s")
            result[metric["name"]] = data

        return result

    def collect_and_save_metrics(self, output_file, cluster_name, start_time, end_time, stage_name):
        prometheus_url = self.config_manager.get_cluster_by_name(cluster_name)[
            'prometheus_url']

        metrics = self.config_manager.metrics

        metrics_result = []

        knative_metrics = self.collect_knative_metrics(
            prometheus_url, metrics, start_time, end_time)
        for metric_to_collect in metrics:
            for data_series in knative_metrics[metric_to_collect["name"]]:
                for point in data_series["values"]:
                    metrics_result.append({"timestamp": datetime.fromtimestamp(float(
                        point[0])), "name": metric_to_collect["name"], "value": float(point[1]), "metric": data_series["metric"]})

        # Save metrics to CSV
        self._save_metrics_to_csv(
            metrics_result, output_file, cluster_name, stage_name)
