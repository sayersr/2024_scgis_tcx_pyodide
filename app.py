from shiny import App, ui, render, reactive
import folium
import gpxpy
import gpxpy.gpx
import xml.etree.ElementTree as ET
import io

app_ui = ui.page_fluid(
    ui.panel_title("TCX File Viewer"),
    ui.input_file("tcx_file", "Upload TCX file", accept=[".tcx"]),
    ui.output_ui("map_output")
)

def server(input, output, session):
    
    @reactive.Calc
    def load_tcx():
        if not input.tcx_file():
            return None
        
        file = input.tcx_file()
        with open(file[0]["datapath"], "r") as f:
            file_content = f.read()
        gpx = gpxpy.parse(convert_tcx_to_gpx(file_content))
        return gpx

    @render.ui
    def map_output():
        gpx = load_tcx()
        if gpx is None:
            return "Please upload a TCX file."
        
        map = folium.Map()
        points = []
        
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points.append((point.latitude, point.longitude))
        
        folium.PolyLine(points, color="red", weight=2.5, opacity=1).add_to(map)
        map.fit_bounds(points)
        
        return ui.HTML(map._repr_html_())

def convert_tcx_to_gpx(tcx_content):
    tcx_root = ET.fromstring(tcx_content)
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    namespace = {'ns': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}
    
    for trackpoint in tcx_root.findall('.//ns:Trackpoint', namespace):
        lat = trackpoint.find('ns:Position/ns:LatitudeDegrees', namespace)
        lon = trackpoint.find('ns:Position/ns:LongitudeDegrees', namespace)
        if lat is not None and lon is not None:
            point = gpxpy.gpx.GPXTrackPoint(
                latitude=float(lat.text),
                longitude=float(lon.text)
            )
            segment.points.append(point)

    return gpx.to_xml()

app = App(app_ui, server)
