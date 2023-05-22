import time
import concurrent.futures
import csv
from kubernetes import client
from datetime import datetime


import requests


class BenchmarkingOrchestrator:
    def __init__(self, config_manager, resource_provisioner):
        self.config_manager = config_manager
        self.resource_provisioner = resource_provisioner

    def _get_service_url(self, app_name, api_client, max_retries=30, retry_interval=1):
        knative_api = client.CustomObjectsApi(api_client=api_client)

        for _ in range(max_retries):
            service = knative_api.get_namespaced_custom_object(group="serving.knative.dev",
                                                               version="v1",
                                                               namespace="default",
                                                               plural="services",
                                                               name=app_name)

            try:
                print("Connecting to service...")
                url = service['status']['url']
                return url
            except KeyError:
                # Wait and try again
                time.sleep(retry_interval)

        # If retries are exhausted, return None
        return None

    def _save_request_results(self, results, output_file=f"results/result_{int(datetime.now().timestamp())}.csv"):
        with open(output_file, "a", newline="") as csvfile:
            writer = csv.writer(csvfile)
            for res in results:
                writer.writerow(
                    [res["request_start"], res["response_timestamp"], res["status_code"], res["response"]])

    def _send_requests(self, app_url, concurrency, duration, post_data=None):
        # Spawn the workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(
                self._send_requests_loop, app_url, duration, post_data) for _ in range(concurrency)]

            # Collect results from all workers
            results = [r for future in futures for r in future.result()]

        self._save_request_results(results)

    def _send_requests_loop(self, app_url, duration, post_data=None):
        loop_results = []
        start_time = time.time()

        while time.time() - start_time < duration:
            result = self._send_single_request(app_url, post_data)
            loop_results.append(result)

        return loop_results

    def _send_single_request(self, app_url, post_data=None):
        headers = {"Content-Type": "application/json"}

        request_start = datetime.utcnow()

        try:
            response = requests.post(app_url, json=post_data, headers=headers)
            response.raise_for_status()

            result = {
                "request_start": request_start,
                "response_timestamp": datetime.utcnow(),
                "status_code": response.status_code,
                "response": response.text,
            }

        except requests.exceptions.RequestException as e:
            result = {
                "request_start": request_start,
                "response_timestamp": datetime.utcnow(),
                "status_code": e.response.status_code,
                "response": str(e),
            }
            time.sleep(0.5)

        return result

    def run_benchmark(self, scenario_name):
        scenario = self.config_manager.get_scenario_by_name(scenario_name)

        for stage in self.resource_provisioner.deploy_scenario(scenario):
            print(f"Running stage '{stage['name']}'")
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

            post_data = {
                "data": {
                    "value": 10
                }
            }
            self._send_requests(app_url, stage["concurrency"],
                                stage["stage_duration"], post_data)