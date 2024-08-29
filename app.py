from shiny import App, ui, render, reactive
import folium
import gpxpy
import gpxpy.gpx
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import datetime
import os

app_ui = ui.page_fluid(
    ui.panel_title("TCX File Viewer"),
    ui.input_file("tcx_files", "Upload TCX files", accept=[".tcx"], multiple=True),
    ui.output_ui("file_info"),
    ui.output_ui("map_output"),
    ui.output_plot("heart_rate_plot")
)

def server(input, output, session):
    
    @reactive.Calc
    def load_tcx_files():
        if not input.tcx_files():
            return None
        
        files = input.tcx_files()
        data = []
        for file in files:
            with open(file["datapath"], "r") as f:
                file_content = f.read()
            gpx, heart_rates, start_time, duration = convert_tcx_to_gpx(file_content)
            max_hr = max(heart_rates) if heart_rates else 0
            data.append({
                "name": os.path.basename(file["name"]),
                "gpx": gpx,
                "heart_rates": heart_rates,
                "start_time": start_time,
                "duration": duration,
                "max_hr": max_hr
            })
        return data

    @render.ui
    def file_info():
        data = load_tcx_files()
        if data is None:
            return "Please upload TCX files."
        
        info_html = "<h3>File Information:</h3>"
        for file_data in data:
            info_html += f"<p><strong>{file_data['name']}</strong><br>"
            info_html += f"Date: {file_data['start_time'].strftime('%Y-%m-%d %H:%M:%S')}<br>"
            info_html += f"Duration: {str(file_data['duration']).split('.')[0]}<br>"
            info_html += f"Maximum Heart Rate: {file_data['max_hr']} bpm</p>"
        
        return ui.HTML(info_html)

    @render.ui
    def map_output():
        data = load_tcx_files()
        if data is None:
            return "Please upload TCX files."
        
        map = folium.Map()
        colors = ['red', 'blue', 'green', 'purple', 'orange']  # Add more colors if needed
        
        for idx, file_data in enumerate(data):
            points = []
            for track in file_data['gpx'].tracks:
                for segment in track.segments:
                    for point in segment.points:
                        points.append((point.latitude, point.longitude))
            
            folium.PolyLine(points, color=colors[idx % len(colors)], weight=2.5, opacity=1).add_to(map)
        
        # Fit bounds to include all tracks
        all_points = [point for file_data in data for track in file_data['gpx'].tracks for segment in track.segments for point in segment.points]
        if all_points:
            map.fit_bounds([(p.latitude, p.longitude) for p in all_points])
        
        return ui.HTML(map._repr_html_())

    @render.plot
    def heart_rate_plot():
        data = load_tcx_files()
        if data is None:
            return None
        
        fig, ax = plt.subplots(figsize=(12, 6))
        colors = ['red', 'blue', 'green', 'purple', 'orange']  # Add more colors if needed
        
        for idx, file_data in enumerate(data):
            time_labels = [str(datetime.timedelta(seconds=s)) for s in range(len(file_data['heart_rates']))]
            ax.plot(time_labels, file_data['heart_rates'], color=colors[idx % len(colors)], label=file_data['name'])
        
        ax.set_xlabel("Time (hours:minutes:seconds)")
        ax.set_ylabel("Heart Rate (bpm)")
        ax.set_title("Heart Rate Over Time")
        
        plt.xticks(rotation=45, ha='right')
        
        # Show only a subset of x-axis labels to avoid overcrowding
        num_ticks = 10
        tick_indices = [i for i in range(0, len(time_labels), len(time_labels) // num_ticks)]
        plt.xticks(tick_indices, [time_labels[i] for i in tick_indices])
        
        plt.legend()
        plt.tight_layout()
        return fig

def convert_tcx_to_gpx(tcx_content):
    tcx_root = ET.fromstring(tcx_content)
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    namespace = {'ns': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}
    
    heart_rates = []
    start_time = None
    end_time = None
    
    for trackpoint in tcx_root.findall('.//ns:Trackpoint', namespace):
        time = trackpoint.find('ns:Time', namespace)
        lat = trackpoint.find('ns:Position/ns:LatitudeDegrees', namespace)
        lon = trackpoint.find('ns:Position/ns:LongitudeDegrees', namespace)
        hr = trackpoint.find('ns:HeartRateBpm/ns:Value', namespace)
        
        if time is not None:
            current_time = datetime.datetime.fromisoformat(time.text)
            if start_time is None:
                start_time = current_time
            end_time = current_time
        
        if lat is not None and lon is not None:
            point = gpxpy.gpx.GPXTrackPoint(
                latitude=float(lat.text),
                longitude=float(lon.text)
            )
            segment.points.append(point)
        
        if hr is not None:
            heart_rates.append(int(hr.text))

    duration = end_time - start_time if start_time and end_time else datetime.timedelta()
    return gpx, heart_rates, start_time, duration

app = App(app_ui, server)
