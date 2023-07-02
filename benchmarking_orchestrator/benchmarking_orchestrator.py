import time
import concurrent.futures
import csv
import os
from kubernetes import client
from datetime import datetime

from metrics_collector import MetricsCollector

import requests


class BenchmarkingOrchestrator:
    def __init__(self, config_manager, resource_provisioner):
        self.config_manager = config_manager
        self.resource_provisioner = resource_provisioner
        self.metrics_collector = MetricsCollector(config_manager)

    def _get_service_url(self, app_name, api_client, max_retries=30, retry_interval=1):
        knative_api = client.CustomObjectsApi(api_client=api_client)

        for _ in range(max_retries):
            service = knative_api.get_namespaced_custom_object(group="serving.knative.dev",
                                                               version="v1",
                                                               namespace="default",
                                                               plural="services",
                                                               name=app_name)

            try:
                print(f"Waiting for service {app_name}...")
                url = service['status']['url']
                return url
            except KeyError:
                # Wait and try again
                time.sleep(retry_interval)

        # If retries are exhausted, return None
        return None

    def save_request_results(self, results, stage, output_file=f"results/result_{int(datetime.now().timestamp())}.csv"):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            for res in results:
                writer.writerow(
                    [res["request_start"], res["response_timestamp"], stage, res["status_code"], res["response"]])

    def _send_requests(self, app_url, start_concurrency, end_concurrency, sleep_time=0, time_between_worker_spawns=0, duration=10, post_data=None):
        # Initialize results list and start time
        end_concurrency = start_concurrency if end_concurrency is None else end_concurrency
        overall_results = []
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=end_concurrency) as executor:
            # List for storing futures
            futures = []

            # Spawning initial workers equal to start_concurrency
            for _ in range(start_concurrency):
                futures.append(executor.submit(
                    self._send_requests_loop, app_url, start_time, duration, int(sleep_time)))

            # After starting the initial workers sleep for `time_between_worker_spawns`
            time.sleep(time_between_worker_spawns)

            # Spawning additional workers up to end_concurrency
            for current_concurrency in range(start_concurrency + 1, end_concurrency + 1):
                if time.time() - start_time >= duration:
                    break
                futures.append(executor.submit(
                    self._send_requests_loop, app_url, start_time, duration, int(sleep_time)))

                # Wait for next worker spawn.
                time.sleep(time_between_worker_spawns)

            # Aggregating results from all workers
            for future in futures:
                overall_results.extend(future.result())

        return overall_results

    def _send_requests_loop(self, app_url, start_time, duration, sleep_time):
        print("Spawned worker")
        loop_results = []

        while time.time() - start_time < duration:
            result = self._send_single_request(app_url, sleep_time)
            loop_results.append(result)

        return loop_results

    def _send_single_request(self, app_url, sleep_time):
        headers = {"Content-Type": "application/json"}

        request_start = datetime.now()

        try:
            response = requests.post(
                app_url, json={"data": {"value": 10}}, headers=headers)
            response.raise_for_status()

            result = {
                "request_start": request_start,
                "response_timestamp": datetime.now(),
                "status_code": response.status_code,
                "response": response.text,
            }
            if sleep_time > 0:
                time.sleep(sleep_time)

        except requests.exceptions.RequestException as e:
            if (e is None or e.response is None):
                result = {
                    "request_start": request_start,
                    "response_timestamp": datetime.now(),
                    "status_code": 500,
                    "response": str(e),
                }
            else:
                result = {
                    "request_start": request_start,
                    "response_timestamp": datetime.now(),
                    "status_code": e.response.status_code,
                    "response": str(e),
                }
            time.sleep(0.5)

        return result

    def run_benchmark(self, scenario_name):
        scenario = self.config_manager.get_scenario_by_name(scenario_name)
        timestamp = int(datetime.now().timestamp())
        output_metrics_file = f"results/{scenario_name}/metrics_{timestamp}.csv"
        output_results_file = f"results/{scenario_name}/results_{timestamp}.csv"

        for stage in self.resource_provisioner.deploy_scenario(scenario):
            print(f"Running stage '{stage['name']}'")
            stage_start_time = datetime.now()

            app_name = stage["app_target"]

            # Iterate through apps and find the target cluster
            api_client = None
            for app in stage["apps"]:
                if app["name"] == app_name:
                    cluster = self.config_manager.get_cluster_by_name(
                        app["cluster"])
                    api_client = self.config_manager.load_kube_config(cluster)
                    break
            else:
                raise Exception(f"Target app '{app_name}' not found in stage")

            app_url = self._get_service_url(app_name, api_client)
            if not app_url:
                raise Exception(f"Failed to get URL for app '{app_name}'")

            results = self._send_requests(app_url, stage["concurrency"], stage["max_concurrency"], stage["sleep_time"] if "sleep_time" in stage else 0, stage["time_between_concurrency"],
                                          stage["stage_duration"])
            stage_end_time = datetime.now()

            # Saving metrics
            self.save_request_results(
                results, stage['name'], output_results_file)

            for cluster in self.config_manager.clusters:
                print(
                    f"Collecting metrics from cluster '{cluster['name']}' and saving to '{output_metrics_file}'")
                self.metrics_collector.collect_and_save_metrics(
                    output_metrics_file, cluster['name'], stage_start_time, stage_end_time, stage['name'])
