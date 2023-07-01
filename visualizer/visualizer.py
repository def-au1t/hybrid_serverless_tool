import matplotlib.pyplot as plt
import pandas as pd


class Visualizer:

    def __init__(self, data_aggregator):
        self.data_aggregator = data_aggregator

        self.results_df = data_aggregator.results_df
        self.cluster_metrics_df = data_aggregator.cluster_metrics_df
        self.knative_metrics_df = data_aggregator.knative_metrics_df
        self.scenario_name = data_aggregator.scenario_name
        self.stage_start_times = self.find_stage_start_times()

    def visualize(self):
        self.plot_results_mean_processing_aggregated_chart()
        self.plot_results_mean_latency_aggregated_chart()
        self.plot_clusters_metrics()
        self.plot_knative_metrics()
        self.plot_results_throughput_aggregated_chart()
        self.print_stages_times()

    def find_stage_start_times(self):
        df = self.results_df.copy()
        df['start_time'] = pd.to_datetime(df['start_time'])
        return df.sort_values(by='start_time').groupby(
            'stage').first().reset_index()[['stage', 'start_time']]

    def plot_results_throughput_aggregated_chart(self, df=None):
        output_file = f'./results/{f"{self.scenario_name}/" if self.scenario_name else ""}chart_thoughput.png'
        df = self.results_df.copy() if df is None else df

        df = self.results_df.copy()
        df.drop('stage', axis=1, inplace=True)
        # Convert 'start_time' column to DateTime type
        df['start_time'] = pd.to_datetime(df['start_time'])

        # Set 'start_time' as the DataFrame index
        df.set_index('start_time', inplace=True)

        # Resample the data in 1-second intervals and count the number of requests for each response code
        df_resampled = df.resample(
            '1S')['status_code'].value_counts().unstack(fill_value=0)

        # Create a figure and axis
        fig, ax = plt.subplots(figsize=(12, 8))

        # Plot lines for each response code
        for code in df_resampled.columns:
            ax.plot(df_resampled.index,
                    df_resampled[code], label=f'Response Code: {code}')

        # Plot vertical lines for the stage start times
        for _, row in self.stage_start_times.iterrows():
            plt.axvline(row['start_time'], color='gray', linestyle='--')

        ax.set_xlabel('Time')
        ax.set_ylabel('Req/Sec')
        ax.set_title('Throughput (requests per second)')

        # Add a legend
        ax.legend()

        # plt.show()
        plt.savefig(output_file)

    def plot_results_mean_processing_aggregated_chart(self, df=None, ):

        df = self.results_df.copy() if df is None else df
        output_file = f'./results/{f"{self.scenario_name}/" if self.scenario_name else ""}chart_mean_processing_stages.png'

        # drop stage column
        df.drop('stage', axis=1, inplace=True)

        # Set 'start_time' as the DataFrame index
        df.set_index('start_time', inplace=True)

        # Resample the data in 2-second batches and calculate the mean
        df_resampled = df.resample('2S').mean()

        df_resampled['total_time'] = df_resampled['total_time'] / 1e6

        # # Plot the line chart
        plt.figure(figsize=(12, 8))

        # Plot dotted lines for stage 1, stage 2, and stage 3 processing time
        plt.plot(df_resampled.index,
                 df_resampled['stage_1_processing_time'], 'r:', label='Stage 1 Calculations Time')
        plt.plot(df_resampled.index,
                 df_resampled['stage_2_processing_time'], 'g:', label='Stage 2 Calculations Time')
        plt.plot(df_resampled.index,
                 df_resampled['stage_3_processing_time'], 'b:', label='Stage 3 Calculations Time')

        # Plot lines with corresponding colors for total stage 1, stage 2, and stage 3 processing times
        plt.plot(df_resampled.index,
                 df_resampled['stage_1_total'], 'r', label='Total Stage 1 Time')
        plt.plot(df_resampled.index,
                 df_resampled['stage_2_total'], 'g', label='Total Stage 2 Time (REQ to RES)')
        plt.plot(df_resampled.index,
                 df_resampled['stage_3_total'], 'b', label='Total Stage 3 Time (REQ to RES)')

        # Plot lines for 'total_time'
        plt.plot(df_resampled.index,
                 df_resampled['total_time'], 'k', label='Total Time')

        # Plot vertical lines for the stage start times
        for _, row in self.stage_start_times.iterrows():
            plt.axvline(row['start_time'], color='gray', linestyle='--')

        #  log scale for y axis
        plt.yscale('log')

        plt.xlabel('Time')
        plt.ylabel('Processing Time (miliseconds)')
        plt.title('Aggregated Mean Processing Times')
        plt.legend()
        # plt.show()
        plt.savefig(output_file)

    def plot_results_mean_latency_aggregated_chart(self, df=None):

        df = self.results_df.copy() if df is None else df
        output_file = f'./results/{f"{self.scenario_name}/" if self.scenario_name else ""}chart_mean_latency_stages.png'

        # drop stage column
        df.drop('stage', axis=1, inplace=True)

        # Set 'start_time' as the DataFrame index
        df.set_index('start_time', inplace=True)

        # Resample the data in 2-second batches and calculate the mean
        df_resampled = df.resample('2S').mean()

        df_resampled['total_time'] = df_resampled['total_time'] / 1e6

        # # Plot the line chart
        plt.figure(figsize=(12, 8))

        plt.plot(df_resampled.index,
                 df_resampled['stage_1_latency_start'], 'r--', label='Stage 1 Latency Start')
        plt.plot(df_resampled.index,
                 df_resampled['stage_1_latency_response'], 'r-.', label='Stage 1 Latency Response')
        plt.plot(df_resampled.index,
                 df_resampled['stage_2_latency_start'], 'g--', label='Stage 2 Latency Start')
        plt.plot(df_resampled.index,
                 df_resampled['stage_2_latency_response'], 'g-.', label='Stage 2 Latency Response')
        plt.plot(df_resampled.index,
                 df_resampled['stage_3_latency_start'], 'b--', label='Stage 3 Latency Start')
        plt.plot(df_resampled.index,
                 df_resampled['stage_3_latency_response'], 'b-.', label='Stage 3 Latency Response')

        # Plot vertical lines for the stage start times
        for _, row in self.stage_start_times.iterrows():
            plt.axvline(row['start_time'], color='gray', linestyle='--')

        plt.yscale('log')

        plt.xlabel('Time')
        plt.ylabel('Latency Time (miliseconds)')
        plt.title('Mean Latency Times')
        plt.legend()
        # plt.show()
        plt.savefig(output_file)

    def plot_clusters_metrics(self, df=None):
        df = self.cluster_metrics_df.copy() if df is None else df
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        output_file = f'./results/{f"{self.scenario_name}/" if self.scenario_name else ""}chart_clusters_metrics.png'
        # Group the data by 'cluster'
        grouped = df.groupby('cluster')

        # Define line styles and colors
        line_styles = ['-', '--', '-.', ':']
        colors = ['red', 'green', 'blue', 'orange']

        # Create subplots with shared x-axis
        fig, ax1 = plt.subplots(figsize=(12, 8))
        ax2 = ax1.twinx()

        # Plot 'cpu' on the first axis
        for i, (name, group) in enumerate(grouped):
            ax1.plot(group['timestamp'], group['cpu'], linestyle=line_styles[0],
                     color=colors[i % len(colors)], label=name)
            ax2.plot(group['timestamp'], group['memory'],
                     linestyle=line_styles[1], color=colors[i % len(colors)], label=name)

        ax1.set_xlabel('Timestamp')
        ax1.set_ylabel('CPU')
        ax1.set_title('CPU and Memory Usage by Cluster')

        ax2.set_ylabel('Memory [GB]')
        ax2.tick_params(axis='y')

        # Plot vertical lines for the stage start times
        for _, row in self.stage_start_times.iterrows():
            plt.axvline(row['start_time'], color='gray', linestyle='--')

        # Adjust the spacing between subplots
        fig.tight_layout()

        # Show the legend for both axes
        ax1.legend(loc='upper left', title="CPU")
        ax2.legend(loc='upper right', title="Memory")

        plt.savefig(output_file)

    def plot_knative_metrics(self, df=None):
        df = self.knative_metrics_df.copy() if df is None else df
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        output_file = f'./results/{f"{self.scenario_name}/" if self.scenario_name else ""}chart_knative_metrics.png'

        # Group the data by 'service', 'metric_name', and 'timestamp' and calculate the sum of 'metric_value'
        grouped = df.groupby(
            ['service', 'metric_name', 'timestamp']).sum().reset_index()

        # Get unique services and assign a color to each service
        services = grouped['service'].unique()
        colors = ['red', 'green', 'blue', 'orange']

        # Create a figure and axis
        fig, ax = plt.subplots(figsize=(12, 8))

        # Plot lines for each service and metric
        for service, color in zip(services, colors):
            service_group = grouped[grouped['service'] == service]

            # Get unique metrics within the service and assign a line style to each metric
            metrics = service_group['metric_name'].unique()

            line_styles = ['-', '--', '-.', ':']

            # Plot lines for each metric within the service
            for metric, style in zip(metrics, line_styles):
                metric_group = service_group[service_group['metric_name'] == metric]
                ax.plot(metric_group['timestamp'], metric_group['metric_value'],
                        linestyle=style, color=color, label=f'{service} - {metric}')

        # Plot vertical lines for the stage start times
        for _, row in self.stage_start_times.iterrows():
            plt.axvline(row['start_time'], color='gray', linestyle='--')

        ax.set_xlabel('Timestamp')
        ax.set_ylabel('Metric Value')
        ax.set_title('Knative Pods count')

        # Add a legend
        ax.legend()

        plt.savefig(output_file)

    def print_box_plots_for_stages(self, input_df, columns, title, filename):
        output_file = f'./results/{f"{self.scenario_name}/" if self.scenario_name else ""}chart_{filename}.png'

        df = input_df.copy()
        df['total_time'] = pd.to_timedelta(df['total_time'])
        df['total_time_ms'] = df['total_time'].dt.total_seconds() * 1000

        grouped_df = df.dropna(subset=columns).groupby(
            'stage')[columns]

        # Build the box plot
        fig, ax = plt.subplots(figsize=(9, 6))

        # For each group, plot
        for i, (stage, data) in enumerate(grouped_df):
            ax.violinplot(data.values, positions=[
                          i*4+j for j in range(len(columns))], widths=9/(len(columns)*5), showextrema=True, showmedians=True)

        # Set stage names as xticklabels
        ax.set_xticks([i*4+(len(columns)//2) for i in range(len(grouped_df))])
        ax.set_xticklabels(grouped_df.groups.keys())

        # lgo scale
        ax.set_yscale('log')

        plt.xlabel('Stage')
        plt.ylabel('Value')
        plt.title(title)
        plt.grid(True)
        # plt.show()
        plt.savefig(output_file)

    def print_stages_times(self, df=None):
        df = self.results_df.copy() if df is None else df
        self.print_box_plots_for_stages(df, ['stage_1_total', 'stage_2_total', 'stage_3_total'],
                                        'Processing stages total time for each experiment', 'stages_total_time')

        self.print_box_plots_for_stages(df, ['stage_1_processing_time', 'stage_2_processing_time',
                                             'stage_3_processing_time'], "Compute time for each experiment", 'stages_compute_time')

        self.print_box_plots_for_stages(df, ['stage_1_latency_response', 'stage_2_latency_response', 'stage_3_latency_response'],
                                        "Latency time for each experiment", 'stages_latency_time')

        self.print_box_plots_for_stages(df, ['total_time_ms'],
                                        "Total time for each experiment", 'total_time_ms')
