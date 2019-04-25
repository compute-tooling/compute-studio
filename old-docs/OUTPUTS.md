# Outputs



Projects should return outputs that are in the following format:



```json
{
  "renderable": [
    {
      "media_type": "PNG",
      "title": "My PNG",
      "data": "picture bytes here..."
		}
  ],
  "downloadable": [
    {
      "media_type": "CSV",
      "title": "My CSV",
      "data": "comma,sep,values\n"
    }
  ]
}
```



There are two categories of outputs: "renderable" and "downloadable." Renderable outputs will be displayed on the outputs page while downloadable outputs are saved by the user as a zipfile. These categories are represented as the two top-level members in the JSON structure above. They point to a `List` of `Output Objects`.  Each `Output Object` has three members: `media_type`, `title`, and `data`.  Supported media types are:

- [`bokeh`](#bokeh)
- [`table`](#table)
- [`CSV`](#CSV)
- `PNG`
- `JPEG`
- `MP3`
- `MP4`



Here's an example for how to create a full result in Python:

```python
def append_output(df, title, renderable, downloadable):
  	js, div = make_my_plot(df, title)
    renderable.append(
        {
            "media_type": "bokeh",
            "title": title,
            "data": {
                "javascript": js,
                "html": div
            }
        }
    )
    downloadable.append(
        {
            "media_type": "CSV",
            "title": title,
            "data": df.to_csv()
        }
    )
    
downloadable = []
renderable = []

append_output(my_df, "My results", renderable, downloadable)
append_output(my_other_df, "My other results", renderable, downloadable)
```

A full example can be found in the [Matchups package](https://github.com/hdoupe/Matchups/blob/009d7e698f773fa28f41a574141a3c18d1bacf62/matchups/matchups.py#L61-L83).



## Examples



### bokeh



- JSON format:

  ```json
  {
    "media_type": "bokeh",
    "title": "My Bokeh Plot",
    "data": {
      "html": "<div>...</div>",
      "js": "<script>...</script>"
    }
  }
  
  ```

- Python example:

  ```python
  from bokeh.plotting import figure
  from bokeh.embed import components
  
  # see: https://bokeh.pydata.org/en/latest/docs/user_guide/quickstart.html#getting-started
  
  # prepare some data
  x = [1, 2, 3, 4, 5]
  y = [6, 7, 2, 4, 5]
  
  # create a new plot with a title and axis labels
  p = figure(title="simple line example", x_axis_label='x', y_axis_label='y')
  
  # add a line renderer with legend and line thickness
  p.line(x, y, legend="Temp.", line_width=2)
  
  # get the results
  js, div = components(p)
  
  output = {
    "media_type": "bokeh",
    "title": "simple line example",
    "data": {
      "html": div,
      "js": js
    }
  }
  ```

  

### table

- JSON format:

  ```json
  {
    "media_type": "table",
    "title": "My Table",
    "data": "<table>...</table>"
  }
  ```

- Python example:

  ```python
  import pandas as pd
  
  df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
  table = df.to_html()
  
  output = {
      "media_type": "table",
      "title": "My Table",
      "data": table
  }
  ```



### CSV

- JSON format:

  ```json
  {
    "media_type": "table",
    "title": "My Table",
    "data": "<table>...</table>"
  }
  ```

- Python example:

  ```python
  import pandas as pd
  
  df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
  csv = df.to_csv()
  
  output = {
      "media_type": "table",
      "title": "My Table",
      "data": csv
  }
  ```

  