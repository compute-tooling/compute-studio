# Data-Viz Guide

Publishing a data-visualization app is a quick way to take something that is running in a notebook or script and make it available to your colleagues or the public-at-large.

You can publish Dash and Bokeh apps on C/S, and we plan to support even more viz libraries like Streamlit and RStudio.

## Dash

_Full source code for app available [here](https://github.com/hdoupe/cs-dash-demo)._

### 1. Create your app.

We are going to use an example app from the [Dash documentation](https://dash.plotly.com/basic-callbacks). The only changes required are setting the `url_base_pathname` for the app and setting the `server` variable:

```python
url_base_pathname = os.environ.get("URL_BASE_PATHNAME", "/")

app = dash.Dash(
    url_base_pathname=url_base_pathname,
    external_stylesheets=external_stylesheets,
)

# This will be called by gunicorn when serving the app on C/S.
server = app.server

```

C/S will set the `URL_BASE_PATHNAME` environment variable when it runs your app. Here's a full working Dash App that you can run locally with this command:

```python
python app.py
```

And, here is the source code:

```python
# app.py

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

# This will be called by gunicorn when serving the app on C/S.
server = app.server

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

Once you've set up a git repository, you can quickly publish an app on C/S. First, create a new file named `app.py` and add the above code to it.

Next, install the compute-studio-kit CLI tool to initialize your Compute Studio configuration:

```
pip install -U cs-kit
```

Now, create the configuration:

```
csk init --app-type data-viz
```

Now your git repository should look like this:

```bash
$ tree .
.
├── app.py
└── cs-config
    └── install.sh

1 directory, 2 files

```

The `app.py` file contains the code from the above example, and `install.sh` is where you will add your app's installation instructions:

```bash
# bash commands for installing your package
pip install -U dash
```

Check out the [environment docs](/publish/environment/) to learn more about the `install.sh` script.

### 3. Publish your app on C/S.

The Compute Studio publish page will walk you through the final steps for creating your app: [https://compute.studio/new/](https://compute.studio/new/)

### 4. The C/S team will take over from here to get your app online as soon as possible!

## Bokeh

_Full source code for app available [here](https://github.com/hdoupe/cs-bokeh-demo)._

### 1. Create your app.

We are going to use an example app from the [Bokeh documentation](https://demo.bokeh.org/).

Here's a full working Bokeh App that you can run locally with this command:

```
bokeh serve app.py
```

And, here is the source code:

````python
# app.py

# Downloaded from: https://github.com/bokeh/bokeh/blob/branch-2.3/examples/app/sliders.py

import numpy as np

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, TextInput
from bokeh.plotting import figure

# Set up data
N = 200
x = np.linspace(0, 4*np.pi, N)
y = np.sin(x)
source = ColumnDataSource(data=dict(x=x, y=y))


# Set up plot
plot = figure(plot_height=400, plot_width=400, title="my sine wave",
              tools="crosshair,pan,reset,save,wheel_zoom",
              x_range=[0, 4*np.pi], y_range=[-2.5, 2.5])

plot.line('x', 'y', source=source, line_width=3, line_alpha=0.6)


# Set up widgets
text = TextInput(title="title", value='my sine wave')
offset = Slider(title="offset", value=0.0, start=-5.0, end=5.0, step=0.1)
amplitude = Slider(title="amplitude", value=1.0, start=-5.0, end=5.0, step=0.1)
phase = Slider(title="phase", value=0.0, start=0.0, end=2*np.pi)
freq = Slider(title="frequency", value=1.0, start=0.1, end=5.1, step=0.1)


# Set up callbacks
def update_title(attrname, old, new):
    plot.title.text = text.value

text.on_change('value', update_title)

def update_data(attrname, old, new):

    # Get the current slider values
    a = amplitude.value
    b = offset.value
    w = phase.value
    k = freq.value

    # Generate the new curve
    x = np.linspace(0, 4*np.pi, N)
    y = a*np.sin(k*x + w) + b

    source.data = dict(x=x, y=y)

for w in [offset, amplitude, phase, freq]:
    w.on_change('value', update_data)


# Set up layouts and add to document
inputs = column(text, offset, amplitude, phase, freq)

curdoc().add_root(row(inputs, plot, width=800))
curdoc().title = "Sliders"
```

### 2. Set up your app's git repository.

Once you've set up a git repository, you can quickly publish an app on C/S. First, create a new file named `app.py` and add the above code to it.

Next, install the compute-studio-kit CLI tool to initialize your Compute Studio configuration:

````

pip install -U cs-kit

```

Now, create the configuration:

```

csk init --app-type data-viz

````

Now your git repository should look like this:

```bash
$ tree .
.
├── app.py
└── cs-config
    └── install.sh

1 directory, 2 files

````

The `app.py` file contains the code from the above example, and `install.sh` is where you will add your app's installation instructions:

```bash
# bash commands for installing your package
pip install -U bokeh
```

### 3. Publish your app on C/S.

The Compute Studio publish page will walk you through the final steps for creating your app: [https://compute.studio/new/](https://compute.studio/new/)

### 4. The C/S team will take over from here to get your app online as soon as possible!
