from shiny import App, ui, render, reactive
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
import plotly.io as pio
import plotly.utils
import datetime
import io
import folium
from folium.plugins import MousePosition
import pandas as pd
import numpy as np
import json

# Define a list of contrasting colors
CONTRASTING_COLORS = ['#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#00FFFF', '#FFFF00', '#800000', '#008000', '#000080', '#800080']

app_ui = ui.page_fluid(
    ui.panel_title("TCX Data Viewer"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_file("data_files", "Upload TCX file(s)", accept=[".tcx"], multiple=True),
            ui.output_ui("file_info"),
        ),
        ui.column(12, ui.output_ui("map_output")),
        ui.column(12, ui.output_ui("heart_rate_plot")),
        ui.output_text("debug_info"),
    )
)

def server(input, output, session):
    data = reactive.Value({})
    timeline_data = reactive.Value(pd.DataFrame())
    plot_data = reactive.Value(None)

    @reactive.Effect
    @reactive.event(input.data_files)
    def _():
        files = input.data_files()
        if files is None:
            data.set({})
            return

        processed_data = {}
        all_data = []
        for i, file in enumerate(files):
            file_content = file["datapath"]
            try:
                with open(file_content, "r") as f:
                    file_content = f.read()
                points, heart_rates, start_time, duration, timestamps = convert_tcx(file_content)
                
                valid_heart_rates = [hr for hr in heart_rates if hr is not None]
                max_hr = max(valid_heart_rates) if valid_heart_rates else None
                color = CONTRASTING_COLORS[i % len(CONTRASTING_COLORS)]
                processed_data[file["name"]] = {
                    "points": points,
                    "heart_rates": heart_rates,
                    "start_time": start_time,
                    "duration": duration,
                    "max_hr": max_hr,
                    "color": color,
                    "timestamps": timestamps
                }
                
                # Prepare data for timeline
                df = pd.DataFrame({
                    "timestamp": timestamps,
                    "heart_rate": heart_rates,
                    "lat": [p[0] for p in points],
                    "lon": [p[1] for p in points],
                    "file": file["name"],
                    "color": color
                })
                all_data.append(df)
            except Exception as e:
                print(f"Error processing data for {file['name']}: {str(e)}")
                processed_data[file["name"]] = {"error": f"Error processing data: {str(e)}"}

        data.set(processed_data)
        
        # Combine all data for timeline
        if all_data:
            combined_data = pd.concat(all_data, ignore_index=True)
            # Ensure timestamp column is in datetime format
            combined_data["timestamp"] = pd.to_datetime(combined_data["timestamp"], utc=True)
            # Calculate elapsed time in seconds
            combined_data["elapsed_time"] = (combined_data["timestamp"] - combined_data["timestamp"].min()).dt.total_seconds()
            timeline_data.set(combined_data)

    @output
    @render.ui
    def file_info():
        data_info = data.get()
        if not data_info:
            return "Please upload TCX file(s)."

        info_html = "<h3>Run Data:</h3>"
        for filename, file_data in data_info.items():
            if "error" in file_data:
                info_html += f"<p><strong>{filename}:</strong> Error: {file_data['error']}</p>"
            else:
                info_html += f"<p><strong>{filename}:</strong><br>"
                info_html += f"Date: {file_data['start_time'].strftime('%Y-%m-%d')}<br>"
                info_html += f"Duration: {str(file_data['duration']).split('.')[0]}<br>"
                if file_data['max_hr'] is not None:
                    info_html += f"Max Heart Rate: {file_data['max_hr']} bpm</p>"
                else:
                    info_html += "Heart Rate Data: Not available</p>"
        return ui.HTML(info_html)

    @output
    @render.ui
    def map_output():
        data_info = data.get()
        if not data_info:
            return "No map data available"

        all_points = []
        for file_data in data_info.values():
            if "error" not in file_data:
                all_points.extend(file_data['points'])

        if not all_points:
            return "No valid GPS points found"

        # Calculate the bounding box
        lats, lons = zip(*all_points)
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)

        # Create a map centered on the middle of the bounding box
        m = folium.Map(
            location=[(min_lat + max_lat) / 2, (min_lon + max_lon) / 2],
            zoom_start=12
        )

        for filename, file_data in data_info.items():
            if "error" not in file_data:
                points = file_data['points']
                if points:
                    # Add the track as a polyline
                    folium.PolyLine(points, color=file_data['color'], weight=2.5, opacity=0.8, popup=filename).add_to(m)

                    # Add markers for start and end points
                    folium.Marker(points[0], popup=f"Start - {filename}", icon=folium.Icon(color='green', icon='play')).add_to(m)
                    folium.Marker(points[-1], popup=f"End - {filename}", icon=folium.Icon(color='red', icon='stop')).add_to(m)

        # Add a marker for the current position (will be updated by JavaScript)
        folium.Marker([0, 0], popup="Current Position", icon=folium.Icon(color='purple', icon='info-sign')).add_to(m)

        # Fit the map to the bounding box
        m.fit_bounds([(min_lat, min_lon), (max_lat, max_lon)])

        # Add mouse position display
        MousePosition().add_to(m)

        # Convert the map to HTML
        map_html = m._repr_html_()

        # Wrap the map HTML in a div with a fixed height and width
        return ui.HTML(f"""
        <div id='map' style='height: 800px; width: 100%;'>
            {map_html}
        </div>
        <script>
            // Function to update marker position
            function updateMarkerPosition(lat, lon) {{
                var map = document.getElementById('map')._leaflet_map;
                map.eachLayer(function(layer) {{
                    if(layer instanceof L.Marker && layer.getPopup().getContent() === "Current Position") {{
                        layer.setLatLng([lat, lon]);
                    }}
                }});
            }}
        </script>
        """)

    @output
    @render.ui
    def heart_rate_plot():
        return ui.HTML("""
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <div id="plotly-heart-rate" style="width:100%;height:400px;"></div>
        """)

    @reactive.Effect
    @reactive.event(timeline_data)
    def _():
        data_info = timeline_data.get()
        if data_info.empty:
            plot_data.set(None)
            return

        fig = go.Figure()

        for file_name in data_info['file'].unique():
            file_data = data_info[data_info['file'] == file_name]
            
            # Filter out None values from heart rate data
            valid_data = file_data.dropna(subset=['heart_rate'])
            
            if not valid_data.empty:
                fig.add_trace(go.Scatter(
                    x=valid_data['elapsed_time'],
                    y=valid_data['heart_rate'],
                    mode='lines',
                    name=file_name,
                    line=dict(color=valid_data['color'].iloc[0])
                ))

        fig.update_layout(
            title="Heart Rate Over Time",
            xaxis_title="Time (minutes:seconds)",
            yaxis_title="Heart Rate (bpm)",
            hovermode="x unified",
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        # Update x-axis to show minutes:seconds
        max_time = data_info['elapsed_time'].max()
        tick_values = list(range(0, int(max_time) + 1, max(1, int(max_time // 10))))
        tick_texts = [f"{int(t // 60):02d}:{int(t % 60):02d}" for t in tick_values]

        fig.update_xaxes(
            tickmode='array',
            tickvals=tick_values,
            ticktext=tick_texts
        )

        plot_json = json.dumps(fig.to_dict(), cls=plotly.utils.PlotlyJSONEncoder)
        plot_data.set(plot_json)

    @reactive.Effect
    @reactive.event(plot_data)
    def _():
        plot_json = plot_data.get()
        if plot_json is not None:
            ui.insert_ui(
                ui.tags.script(f"""
                    Plotly.newPlot('plotly-heart-rate', {plot_json});
                    var plotlyDiv = document.getElementById('plotly-heart-rate');
                    plotlyDiv.on('plotly_hover', function(data){{
                        var x = data.points[0].x;
                        Shiny.setInputValue('hover_time', x);
                    }});
                """),
                selector="#plotly-heart-rate",
                where="afterEnd"
            )

    @output
    @render.text
    def debug_info():
        data_info = timeline_data.get()
        if data_info.empty:
            return "No data available for debugging"
        
        debug_str = f"Total rows: {len(data_info)}\n"
        debug_str += f"Columns: {', '.join(data_info.columns)}\n"
        debug_str += f"Heart rate range: {data_info['heart_rate'].min()} - {data_info['heart_rate'].max()}\n"
        debug_str += f"Time range: {data_info['elapsed_time'].min()} - {data_info['elapsed_time'].max()} seconds"
        return debug_str

    @reactive.Effect
    @reactive.event(input.hover_time)
    def _():
        hover_time = input.hover_time()
        data_info = timeline_data.get()
        if not data_info.empty and hover_time is not None:
            current_data = data_info[data_info['elapsed_time'] <= hover_time].iloc[-1]
            
            # Update the map marker position using JavaScript
            ui.insert_ui(
                ui.tags.script(f"""
                    updateMarkerPosition({current_data['lat']}, {current_data['lon']});
                """),
                selector="#map",
                where="afterEnd"
            )

def convert_tcx(tcx_content):
    def parse_xml(content):
        return ET.fromstring(content)

    try:
        tcx_root = parse_xml(tcx_content)
    except ET.ParseError as e:
        raise ValueError(f"Unable to parse TCX data. Error: {str(e)}. Data starts with: {tcx_content[:100]}")

    namespace = {'ns': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}

    data = []
    start_time = None
    end_time = None

    for trackpoint in tcx_root.findall('.//ns:Trackpoint', namespace):
        point = {}

        time = trackpoint.find('ns:Time', namespace)
        if time is not None:
            current_time = datetime.datetime.fromisoformat(time.text)
            if start_time is None:
                start_time = current_time
            end_time = current_time
            point['timestamp'] = current_time

        lat = trackpoint.find('ns:Position/ns:LatitudeDegrees', namespace)
        lon = trackpoint.find('ns:Position/ns:LongitudeDegrees', namespace)
        if lat is not None and lon is not None:
            point['lat'] = float(lat.text)
            point['lon'] = float(lon.text)

        hr = trackpoint.find('.//ns:HeartRateBpm/ns:Value', namespace)
        if hr is not None:
            point['heart_rate'] = int(hr.text)

        if point:  # Only append if we have any data for this trackpoint
            data.append(point)

    if not data:
        raise ValueError("No valid data found in the TCX file")

    # Convert to DataFrame for easier processing
    df = pd.DataFrame(data)

    # Ensure all necessary columns exist
    for col in ['timestamp', 'lat', 'lon', 'heart_rate']:
        if col not in df.columns:
            df[col] = None

    # Sort by timestamp
    df = df.sort_values('timestamp')

    # Extract data
    timestamps = df['timestamp'].tolist()
    heart_rates = df['heart_rate'].tolist()
    points = list(zip(df['lat'].fillna(method='ffill'), df['lon'].fillna(method='ffill')))

    duration = end_time - start_time if start_time and end_time else datetime.timedelta()
    
    return points, heart_rates, start_time, duration, timestamps

app = App(app_ui, server)