# Data-Viz Guide

Publishing a data-visualization app is a quick way to take something that is running in a notebook or script and make it available to your colleagues or the public-at-large.

You can publish Dash and Bokeh apps on C/S, and we plan to support even more viz libraries like Streamlit and RStudio.

## Dash

### 1. Create your app.

We are going to use an example app from the [Dash documentation](https://dash.plotly.com/basic-callbacks). The key part is setting the `url_base_pathname` for the app:

```python
url_base_pathname = os.environ.get("URL_BASE_PATHNAME", "/")

app = dash.Dash(
    url_base_pathname=url_base_pathname,
    external_stylesheets=external_stylesheets,
)

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

### 1. Create your app.

We are going to use an example app from the [Bokeh documentation](https://docs.bokeh.org/en/latest/docs/user_guide/server.html#single-module-format).

Here's a full working Bokeh App that you can run locally with this command:

```
bokeh serve myapp.py
```

And, here is the source code:

```python
# myapp.py

from random import random

from bokeh.layouts import column
from bokeh.models import Button
from bokeh.palettes import RdYlBu3
from bokeh.plotting import figure, curdoc

# create a plot and style its properties
p = figure(x_range=(0, 100), y_range=(0, 100), toolbar_location=None)
p.border_fill_color = 'black'
p.background_fill_color = 'black'
p.outline_line_color = None
p.grid.grid_line_color = None

# add a text renderer to our plot (no data yet)
r = p.text(x=[], y=[], text=[], text_color=[], text_font_size="26px",
           text_baseline="middle", text_align="center")

i = 0

ds = r.data_source

# create a callback that will add a number in a random location
def callback():
    global i

    # BEST PRACTICE --- update .data in one step with a new dict
    new_data = dict()
    new_data['x'] = ds.data['x'] + [random()*70 + 15]
    new_data['y'] = ds.data['y'] + [random()*70 + 15]
    new_data['text_color'] = ds.data['text_color'] + [RdYlBu3[i%3]]
    new_data['text'] = ds.data['text'] + [str(i)]
    ds.data = new_data

    i = i + 1

# add a button widget and configure with the call back
button = Button(label="Press Me")
button.on_click(callback)

# put the button and plot in a layout and add to the document
curdoc().add_root(column(button, p))
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
├── myapp.py
└── cs-config
    └── install.sh

1 directory, 2 files

```

The `myapp.py` file contains the code from the above example, and `install.sh` is where you will add your app's installation instructions:

```bash
# bash commands for installing your package
pip install -U bokeh
```

### 3. Publish your app on C/S.

The Compute Studio publish page will walk you through the final steps for creating your app: [https://compute.studio/new/](https://compute.studio/new/)

### 4. The C/S team will take over from here to get your app online as soon as possible!
