from shiny import App, ui, render, reactive
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
import plotly.io as pio
import plotly.utils
import datetime
import io
import pandas as pd
import numpy as np
import json

def convert_tcx(tcx_content):
    root = ET.fromstring(tcx_content)
    ns = {'ns': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}
    
    points = []
    heart_rates = []
    timestamps = []
    
    for trackpoint in root.findall('.//ns:Trackpoint', ns):
        position = trackpoint.find('ns:Position', ns)
        if position is not None:
            lat = float(position.find('ns:LatitudeDegrees', ns).text)
            lon = float(position.find('ns:LongitudeDegrees', ns).text)
            points.append((lat, lon))
            
            heart_rate = trackpoint.find('.//ns:HeartRateBpm/ns:Value', ns)
            heart_rates.append(int(heart_rate.text) if heart_rate is not None else None)
            
            time = trackpoint.find('ns:Time', ns)
            if time is not None:
                timestamps.append(datetime.datetime.fromisoformat(time.text.replace('Z', '+00:00')))
    
    start_time = timestamps[0] if timestamps else None
    duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else datetime.timedelta(0)
    
    return points, heart_rates, start_time, duration, timestamps

# Define a list of contrasting colors
CONTRASTING_COLORS = ['#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#00FFFF', '#FFFF00', '#800000', '#008000', '#000080', '#800080']

app_ui = ui.page_fluid(
    ui.panel_title("TCX Data Viewer"),
    ui.tags.head(
        ui.tags.link(rel="stylesheet", href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css"),
        ui.tags.script(src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"),
    ),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_file("data_files", "Upload TCX file(s)", accept=[".tcx"], multiple=True),
            ui.output_ui("file_info"),
        ),
        ui.column(12, 
            ui.div(
                ui.output_ui("map_output"),
                ui.output_ui("heart_rate_plot"),
                style="display: flex; flex-direction: column; gap: 10px;"
            )
        ),
        ui.output_text("debug_map_info"),
    )
)

def server(input, output, session):
    data = reactive.Value({})
    timeline_data = reactive.Value(pd.DataFrame())
    plot_data_reactive = reactive.Value(None)

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
            # Calculate elapsed time in seconds for each file separately
            combined_data["elapsed_time"] = combined_data.groupby("file")["timestamp"].transform(lambda x: (x - x.min()).dt.total_seconds())
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

        # Calculate the center and zoom level
        lats, lons = zip(*all_points)
        center_lat = (min(lats) + max(lats)) / 2
        center_lon = (min(lons) + max(lons)) / 2

        map_data = {
            "center": [center_lat, center_lon],
            "zoom": 12,
            "tracks": [
                {
                    "name": filename,
                    "color": file_data['color'],
                    "points": file_data['points']
                }
                for filename, file_data in data_info.items()
                if "error" not in file_data
            ]
        }

        return ui.HTML(f"""
        <div id="map" style="height: 400px; width: 100%;"></div>
        <script>
        var mapData = {json.dumps(map_data)};
        var map, currentPositionMarkers = {{}};
        
        function initializeMap() {{
            if (map) {{
                map.remove();
            }}
            map = L.map('map').setView(mapData.center, mapData.zoom);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }}).addTo(map);

            mapData.tracks.forEach(function(track) {{
                L.polyline(track.points, {{color: track.color}}).addTo(map);
                L.marker(track.points[0], {{
                    icon: L.divIcon({{
                        className: 'custom-div-icon',
                        html: `<div style='background-color:${{track.color}};' class='marker-pin'></div><i class='fa fa-circle' style='color: white;'></i>`,
                        iconSize: [30, 42],
                        iconAnchor: [15, 42]
                    }})
                }}).addTo(map).bindPopup('Start - ' + track.name);
                L.marker(track.points[track.points.length - 1], {{
                    icon: L.divIcon({{
                        className: 'custom-div-icon',
                        html: `<div style='background-color:${{track.color}};' class='marker-pin'></div><i class='fa fa-flag' style='color: white;'></i>`,
                        iconSize: [30, 42],
                        iconAnchor: [15, 42]
                    }})
                }}).addTo(map).bindPopup('End - ' + track.name);
            }});
        }}

        // Initialize map after a short delay to ensure the container is ready
        setTimeout(initializeMap, 100);

        function updateMarkerPosition(lat, lon, color, filename) {{
            if (!map) return;
            
            if (!currentPositionMarkers[filename]) {{
                currentPositionMarkers[filename] = L.circleMarker([lat, lon], {{
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.8,
                    radius: 8
                }}).addTo(map);
            }} else {{
                currentPositionMarkers[filename].setLatLng([lat, lon]);
            }}
            map.panTo([lat, lon]);
        }}
        </script>
        """)

    @output
    @render.ui
    def heart_rate_plot():
        return ui.HTML("""
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <div id="plotly-heart-rate" style="width:100%;height:300px;"></div>
        """)

    @reactive.Effect
    @reactive.event(timeline_data)
    def _():
        data_info = timeline_data.get()
        if data_info.empty:
            plot_data_reactive.set(None)
            return

        fig = go.Figure()

        for file_name in data_info['file'].unique():
            file_data = data_info[data_info['file'] == file_name]
            
            # Filter out None values from heart rate data
            valid_data = file_data.dropna(subset=['heart_rate'])
            
            if not valid_data.empty:
                fig.add_trace(go.Scatter(
                    x=valid_data['elapsed_time'] / 60,  # Convert to minutes
                    y=valid_data['heart_rate'],
                    mode='lines',
                    name=file_name,
                    line=dict(color=valid_data['color'].iloc[0])
                ))

        fig.update_layout(
            title="Heart Rate Over Time",
            xaxis_title="Time Elapsed (minutes)",
            yaxis_title="Heart Rate (bpm)",
            hovermode="x unified",
            height=300,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        plot_data_json = json.dumps(fig.data, cls=plotly.utils.PlotlyJSONEncoder)
        layout_data_json = json.dumps(fig.layout, cls=plotly.utils.PlotlyJSONEncoder)
        
        plot_data_reactive.set((plot_data_json, layout_data_json))

    @reactive.Effect
    @reactive.event(plot_data_reactive)
    def update_plot():
        plot_data = plot_data_reactive.get()
        if plot_data is not None:
            plot_data_json, layout_data_json = plot_data
            ui.insert_ui(
                ui.tags.script(f"""
                Plotly.newPlot('plotly-heart-rate', {plot_data_json}, {layout_data_json});
                var plotlyDiv = document.getElementById('plotly-heart-rate');
                plotlyDiv.on('plotly_hover', function(data){{
                    var x = data.points[0].x;
                    Shiny.setInputValue('hover_time', x);
                }});
                """),
                selector="#plotly-heart-rate",
                where="afterEnd"
            )

    @reactive.Effect
    @reactive.event(input.hover_time)
    def _():
        hover_time = input.hover_time()
        data_info = timeline_data.get()
        if not data_info.empty and hover_time is not None:
            # Convert hover_time back to seconds
            hover_time_seconds = hover_time * 60
            current_data = data_info[data_info['elapsed_time'] <= hover_time_seconds].groupby('file').last()
            
            if not current_data.empty:
                # Update the map marker position using JavaScript for each file
                for _, row in current_data.iterrows():
                    ui.insert_ui(
                        ui.tags.script(f"updateMarkerPosition({row['lat']}, {row['lon']}, '{row['color']}', '{row.name}');"),
                        selector="#map",
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
        
app = App(app_ui, server)