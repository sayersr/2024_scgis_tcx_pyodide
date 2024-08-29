from shiny import App, ui, render, reactive
import folium
import gpxpy
import gpxpy.gpx
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import datetime

app_ui = ui.page_fluid(
    ui.panel_title("TCX File Viewer"),
    ui.input_file("tcx_file", "Upload TCX file", accept=[".tcx"]),
    ui.output_ui("map_output"),
    ui.output_plot("heart_rate_plot")
)

def server(input, output, session):
    
    @reactive.Calc
    def load_tcx():
        if not input.tcx_file():
            return None
        
        file = input.tcx_file()
        with open(file[0]["datapath"], "r") as f:
            file_content = f.read()
        return convert_tcx_to_gpx(file_content)

    @render.ui
    def map_output():
        data = load_tcx()
        if data is None:
            return "Please upload a TCX file."
        
        gpx, _ = data
        map = folium.Map()
        points = []
        
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points.append((point.latitude, point.longitude))
        
        folium.PolyLine(points, color="red", weight=2.5, opacity=1).add_to(map)
        map.fit_bounds(points)
        
        return ui.HTML(map._repr_html_())

    @render.plot
    def heart_rate_plot():
        data = load_tcx()
        if data is None:
            return None
        
        _, heart_rates = data
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create time labels for x-axis
        time_labels = [str(datetime.timedelta(seconds=s)) for s in range(len(heart_rates))]
        
        ax.plot(time_labels, heart_rates)
        ax.set_xlabel("Time (hours:minutes:seconds)")
        ax.set_ylabel("Heart Rate (bpm)")
        ax.set_title("Heart Rate Over Time")
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Show only a subset of x-axis labels to avoid overcrowding
        num_ticks = 10
        tick_indices = [i for i in range(0, len(time_labels), len(time_labels) // num_ticks)]
        plt.xticks(tick_indices, [time_labels[i] for i in tick_indices])
        
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
    
    for trackpoint in tcx_root.findall('.//ns:Trackpoint', namespace):
        lat = trackpoint.find('ns:Position/ns:LatitudeDegrees', namespace)
        lon = trackpoint.find('ns:Position/ns:LongitudeDegrees', namespace)
        hr = trackpoint.find('ns:HeartRateBpm/ns:Value', namespace)
        
        if lat is not None and lon is not None:
            point = gpxpy.gpx.GPXTrackPoint(
                latitude=float(lat.text),
                longitude=float(lon.text)
            )
            segment.points.append(point)
        
        if hr is not None:
            heart_rates.append(int(hr.text))

    return gpx, heart_rates

app = App(app_ui, server)
