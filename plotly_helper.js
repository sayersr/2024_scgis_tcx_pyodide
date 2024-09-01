function updateHeartRatePlot(plotData, layoutData) {
  Plotly.newPlot('plotly-heart-rate', JSON.parse(plotData), JSON.parse(layoutData));

  var plotlyDiv = document.getElementById('plotly-heart-rate');
  plotlyDiv.on('plotly_hover', function(data){
    var x = data.points[0].x;
    Shiny.setInputValue('hover_time', x);
  });
}