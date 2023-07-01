import os
import pandas as pd


class DataAggregator:
    def __init__(self, scenario_name):
        self.scenario_name = scenario_name
        self.results_df = self.convert_results_data(
            self.get_most_recent_benchmark_results())
        self.cluster_metrics_df = self.convert_cluster_metrics(
            self.get_most_recent_benchmark_metrics())
        self.knative_metrics_df = self.convert_knative_metrics(
            self.get_most_recent_benchmark_metrics())

    def get_most_recent_file(self, suffix):
        files = os.listdir(f"results/{self.scenario_name}")
        files_results = [f for f in files if suffix in f]
        files_results.sort()
        return f"results/{self.scenario_name}/{files_results[-1]}"

    def get_most_recent_benchmark_results(self):
        return self.get_most_recent_file("results")

    def get_most_recent_benchmark_metrics(self):
        return self.get_most_recent_file("metrics")

    def convert_results_data(self, csv_path):
        df = pd.read_csv(csv_path, header=None)
        df.columns = [
            "start_time", "end_time", "stage", "status_code", "response_data"
        ]

        stage_1_processing_times = []
        stage_2_processing_times = []
        stage_3_processing_times = []
        stage_1_latency_starts = []
        stage_2_latency_starts = []
        stage_3_latency_starts = []
        stage_1_latency_responses = []
        stage_2_latency_responses = []
        stage_3_latency_responses = []
        stage_1_totals = []
        stage_2_totals = []
        stage_3_totals = []
        response_codes = []

        for index, row in df.iterrows():
            stage_1_processing_time = None
            stage_2_processing_time = None
            stage_3_processing_time = None

            stage_1_latency_start = None
            stage_2_latency_start = None
            stage_3_latency_start = None

            stage_1_latency_response = None
            stage_2_latency_response = None
            stage_3_latency_response = None

            stage_1_total = None
            stage_2_total = None
            stage_3_total = None

            response_code = None

            if row["status_code"] == 200:
                response_data = eval(row["response_data"])
                timestamps = response_data["data"]["timestamps"]
                result = response_data["data"]["result"]

                if timestamps["end_3"] != -1 and timestamps["end_2"] != -1 and timestamps["end_1"] != -1:
                    response_code = row["status_code"]
                    stage_1_processing_time = timestamps["send_2"] - \
                        timestamps["start_1"]
                    stage_2_processing_time = timestamps["end_2"] - \
                        timestamps["start_2"]
                    stage_3_processing_time = timestamps["end_3"] - \
                        timestamps["start_3"]

                    stage_1_latency_start = timestamps["start_1"] - pd.to_datetime(
                        row["start_time"], format='%Y-%m-%d %H:%M:%S.%f').timestamp()
                    stage_2_latency_start = timestamps["start_2"] - \
                        timestamps["send_2"]
                    stage_3_latency_start = timestamps["start_3"] - \
                        timestamps["send_3"]
                    stage_1_latency_response = pd.to_datetime(
                        row["end_time"], format='%Y-%m-%d %H:%M:%S.%f').timestamp() - timestamps["end_1"]
                    stage_2_latency_response = timestamps["receive_2"] - \
                        timestamps["end_2"]
                    stage_3_latency_response = timestamps["receive_3"] - \
                        timestamps["end_3"]

                    stage_1_total = timestamps["end_1"] - timestamps["start_1"]
                    stage_2_total = timestamps["receive_2"] - \
                        timestamps["send_2"]
                    stage_3_total = timestamps["receive_3"] - \
                        timestamps["send_3"]
                else:
                    response_code = 500
            else:
                response_code = row["status_code"]
            stage_1_processing_times.append(stage_1_processing_time)
            stage_2_processing_times.append(stage_2_processing_time)
            stage_3_processing_times.append(stage_3_processing_time)
            stage_1_latency_starts.append(stage_1_latency_start)
            stage_2_latency_starts.append(stage_2_latency_start)
            stage_3_latency_starts.append(stage_3_latency_start)
            stage_1_latency_responses.append(stage_1_latency_response)
            stage_2_latency_responses.append(stage_2_latency_response)
            stage_3_latency_responses.append(stage_3_latency_response)
            stage_1_totals.append(stage_1_total)
            stage_2_totals.append(stage_2_total)
            stage_3_totals.append(stage_3_total)
            response_codes.append(response_code)

        new_df = pd.DataFrame({
            "start_time": pd.to_datetime(df["start_time"], format='%Y-%m-%d %H:%M:%S.%f'),
            "total_time": pd.to_datetime(df["end_time"], format='%Y-%m-%d %H:%M:%S.%f') - pd.to_datetime(df["start_time"], format='%Y-%m-%d %H:%M:%S.%f'),
            "stage": df["stage"],
            "status_code": response_codes,
            "stage_1_processing_time": stage_1_processing_times,
            "stage_2_processing_time": stage_2_processing_times,
            "stage_3_processing_time": stage_3_processing_times,
            "stage_1_latency_start": stage_2_latency_starts,
            "stage_2_latency_start": stage_2_latency_starts,
            "stage_3_latency_start": stage_3_latency_starts,
            "stage_1_latency_response": stage_2_latency_responses,
            "stage_2_latency_response": stage_2_latency_responses,
            "stage_3_latency_response": stage_3_latency_responses,
            "stage_1_total": stage_1_totals,
            "stage_2_total": stage_2_totals,
            "stage_3_total": stage_3_totals,
        })

        return new_df

    def convert_cluster_metrics(self, csv_path):
        df = pd.read_csv(csv_path, header=None)
        df.columns = ['timestamp', 'cluster', 'stage',
                      'metric_name', 'metric_value', 'metadata']

        df_filtered = df[df['metadata'] == '{}']
        df_pivoted = df_filtered.pivot_table(
            index=['timestamp', 'cluster'], columns='metric_name', values='metric_value').reset_index()

        return df_pivoted

    def convert_knative_metrics(self, csv_path):
        df = pd.read_csv(csv_path, header=None)
        df.columns = ['timestamp', 'cluster', 'stage',
                      'metric_name', 'metric_value', 'metadata']

        df = df[df['metadata'] != '{}']

        metadata_dict = [eval(meta) for meta in df['metadata']]
        df['service'] = [meta.get('service_name') for meta in metadata_dict]
        df['revision'] = [meta.get('revision_name').split(
            '-')[-1] for meta in metadata_dict]

        df = df[['timestamp', 'stage', 'metric_name',
                 'metric_value', 'service', 'revision']]

        return df
