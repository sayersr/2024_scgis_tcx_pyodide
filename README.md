# TCX Data Viewer

## Overview
The TCX Data Viewer is a Shiny for Python application that allows users to upload and visualize Training Center XML (TCX) files. This app provides an interactive interface to analyze GPS tracks and heart rate data from workouts or activities recorded in TCX format.

## Features
- Upload multiple TCX files simultaneously
- Display a map showing the GPS tracks of all uploaded files
- Plot heart rate data over time for all uploaded files
- Show summary information for each uploaded file, including:
  - Start date and time
  - Duration of the activity
  - Maximum heart rate

## How to Use
1. Launch the application.
2. Use the file upload button to select one or more TCX files from your computer.
3. Once files are uploaded, the app will process them and display:
   - A map showing the GPS tracks of all activities
   - A plot of heart rate data over time for all activities
   - Summary information for each uploaded file

## Map Features
- The map displays the route for each uploaded file in a different color.
- Start points are marked with green markers.
- End points are marked with red markers.
- You can zoom and pan the map to explore the routes in detail.

## Heart Rate Plot Features
- The heart rate data for each file is plotted in a different color.
- The x-axis shows the duration of the activity.
- The y-axis shows the heart rate in beats per minute (BPM).
- A legend identifies which color corresponds to which file.

## Requirements
This app requires the following Python packages:
- shiny
- gpxpy
- matplotlib
- folium
- branca

## Running the App
To run this app locally:
1. Ensure you have all the required packages installed.
2. Run the app.py file using a Python interpreter.

## Note
This app is designed to work with TCX files. Ensure your files are in the correct format for the best experience.

