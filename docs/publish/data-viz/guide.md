# Data-Viz Guide

Publishing a data-visualization app is a quick way to take something that is running in a notebook or script and make it available to your colleagues or the public-at-large.

You can publish Dash and Bokeh apps on C/S, and we plan to support even more viz libraries like Streamlit and RStudio.

## Dash

### 1. Create your app.

We are going to use an example app from the Dash documentation. The key part is setting the `url_base_pathname` for the app:

```python
url_base_pathname = os.environ.get("URL_BASE_PATHNAME", "/")

app = dash.Dash(
    url_base_pathname=url_base_pathname,
    external_stylesheets=external_stylesheets,
)

```

C/S will set the `URL_BASE_PATHNAME` environment variable when it runs your app. The result is that your app will be served from a url that looks like `http://viz.compute.studio/hdoupe/my-dash-app/` instead of `http://viz.compute.studio`.

```python
# Adapted from the Dash docs: https://dash.plotly.com/basic-callbacks

import os
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px

import pandas as pd

df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminderDataFiveYear.csv')

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# Retrieve the variable or set the path to root if it is not there.
url_base_pathname = os.environ.get("URL_BASE_PATHNAME", "/")

app = dash.Dash(
    __name__, external_stylesheets=external_stylesheets, url_base_pathname=url_base_pathname
)

app.layout = html.Div([
    dcc.Graph(id='graph-with-slider'),
    dcc.Slider(
        id='year-slider',
        min=df['year'].min(),
        max=df['year'].max(),
        value=df['year'].min(),
        marks={str(year): str(year) for year in df['year'].unique()},
        step=None
    )
])


@app.callback(
    Output('graph-with-slider', 'figure'),
    [Input('year-slider', 'value')])
def update_figure(selected_year):
    filtered_df = df[df.year == selected_year]

    fig = px.scatter(filtered_df, x="gdpPercap", y="lifeExp",
                     size="pop", color="continent", hover_name="country",
                     log_x=True, size_max=55)

    fig.update_layout(transition_duration=500)

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
```

### 2. Set up your app's git repository.

### 3. Publish your app on C/S.

Fill out the create app form with some basic infromation here: https://compute.studio/new/. This will walk you through a couple steps to get your app published.

### 4. The C/S team will review your app and then publish if it checks out!

## Bokeh
