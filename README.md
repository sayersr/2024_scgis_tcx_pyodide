# TCX Data Viewer

## Overview
The TCX Data Viewer is a Shiny for Python application that allows users to upload and visualize Training Center XML (TCX) files. This app provides an interactive interface to analyze GPS tracks and heart rate data from workouts or activities recorded in TCX format.

## Features
- Upload multiple TCX files simultaneously
- Display an interactive map showing the GPS tracks of all uploaded files
- Plot interactive heart rate data over time for all uploaded files
- Show summary information for each uploaded file, including:
  - Start date and time
  - Duration of the activity
  - Maximum heart rate (if available)
- Interactive data exploration with synchronized map and heart rate plot

## How to Use
1. Launch the application.
2. Use the file upload button to select one or more TCX files from your computer.
3. Once files are uploaded, the app will process them and display:
   - A map showing the GPS tracks of all activities
   - An interactive plot of heart rate data over time for all activities
   - Summary information for each uploaded file in the sidebar
4. Hover over the heart rate plot to see the corresponding location on the map for each activity

## Map Features
- The map displays the route for each uploaded file in a different color.
- Start points are marked with circular markers in the file's color with a black outline.
- End points are marked with circular markers in the file's color with a black outline.
- The map automatically centers and zooms to fit all uploaded tracks.
- Current position markers update as you hover over the heart rate plot.

## Heart Rate Plot Features
- The heart rate data for each file is plotted in a different color.
- The x-axis shows the duration of the activity in minutes.
- The y-axis shows the heart rate in beats per minute (BPM).
- A legend identifies which color corresponds to which file.
- Hover over the plot to see detailed information and update the map markers.

## Requirements
This app requires the following Python packages:
- shiny
- plotly
- pandas
- numpy
- xml.etree.ElementTree

## Running the App
To run this app locally:
1. Ensure you have all the required packages installed.
2. Run the `app.py` file using a Python interpreter.

## Technical Details
- The app uses a colorblind-friendly color palette for distinguishing between multiple files.
- GPS tracks are rendered using Leaflet.js for smooth and interactive map display.
- Heart rate plots are created using Plotly for interactive data visualization.
- The app processes TCX files using Python's built-in XML parsing capabilities.
- Interactive features are implemented using Shiny for Python's reactive programming model.

## Debug Information
The app includes a debug output section that displays:
- Total number of data points processed
- Column names of the processed data
- Heart rate range across all uploaded files
- Time range of the activities in minutes

## Note
This app is designed to work with TCX files. Ensure your files are in the correct format for the best experience. The app handles errors gracefully and will display error messages for files that cannot be processed.

## Shinylive Version

For a web-based version of this application, visit [https://sayersr.github.io/2024_scgis_tcx_pyodide/](https://sayersr.github.io/2024_scgis_tcx_pyodide/). This version uses Shinylive to run the Shiny application directly in your web browser.

## R Version

The R version of this can be found at [https://github.com/sayersr/2024_scgis_tcx_webr](https://github.com/sayersr/2024_scgis_tcx_webr).