"use strict";

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

var BrowserRouter = ReactRouterDOM.BrowserRouter;
var Route = ReactRouterDOM.Route;
var Switch = ReactRouterDOM.Switch;

var md = new Remarkable({
  highlight: function(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(lang, str).value;
      } catch (err) {}
    }

    try {
      return hljs.highlightAuto(str).value;
    } catch (err) {}

    return ""; // use external default escaping
  }
});

function markdownElement(markdownText) {
  const marked = {
    __html: md.render(markdownText)
  };
  return (
    <div className="markdown-wrapper">
      <div
        dangerouslySetInnerHTML={marked}
        className="content card publish markdown"
        style={{ width: "50rem" }}
      />
    </div>
  );
}

class TextField extends React.Component {
  constructor(props) {
    super(props);
  }

  render() {
    var element;
    if (this.props.preview) {
      element = markdownElement(this.props.value);
    } else {
      element = (
        <input
          className="form-control"
          name={this.props.name}
          type={this.props.type}
          value={this.props.value}
          placeholder={this.props.placeholder}
          onChange={this.props.handleChange}
          required
        />
      );
    }
    return (
      <div>
        <p>
          <label>
            <b>{this.props.label}:</b>
            {element}
          </label>
        </p>
      </div>
    );
  }
}

class Description extends React.Component {
  constructor(props) {
    super(props);
  }

  render() {
    const description = this.props.description;
    const charsLeft = 1000 - description.length;
    var element;
    if (this.props.preview) {
      element = markdownElement(description);
    } else {
      element = (
        <textarea
          className="form-control"
          name="description"
          type="text"
          placeholder="What does this app do? Must be less than 1000 characters."
          value={description}
          onChange={this.props.handleChange}
          maxLength="1000"
          style={{ width: "50rem" }}
          // required - shows up red before entering text on firefox?
        />
      );
    }
    return (
      <p className="description">
        <label>
          <b>App overview:</b>
          {element}
        </label>
        <small>{charsLeft}</small>
      </p>
    );
  }
}

class CodeSnippet extends React.Component {
  constructor(props) {
    super(props);
  }

  render() {
    var element;
    if (this.props.preview) {
      const ticks = "```";
      const markdownText = `${ticks}${this.props.language}\n${
        this.props.code
      }\n${ticks}`;
      element = markdownElement(markdownText);
    } else {
      element = (
        <textarea
          className="form-control"
          name={this.props.name}
          type="text"
          placeholder="# code snippet here"
          value={this.props.code}
          onChange={this.props.handleChange}
          style={{ width: "50rem" }}
          // required - shows up red before entering text on firefox?
        />
      );
    }
    return (
      <p>
        <label>
          <b>{this.props.function_name + ":"}</b> {this.props.description}
          {element}
        </label>
      </p>
    );
  }
}

class ServerSize extends React.Component {
  constructor(props) {
    super(props);
    this.handleChange = this.handleChange.bind(this);
  }

  handleChange(event) {
    var [ram, cpu] = event.target.value;
    this.props.handleServerSizeChange(cpu, ram);
  }

  render() {
    return (
      <p>
        <label>
          Choose the server size:
          <select name="server_size" onChange={this.handleChange}>
            <option multiple={true} value={[4, 2]}>
              4 GB 2 vCPUs
            </option>
            <option multiple={true} value={[8, 4]}>
              8 GB 4 vCPUs
            </option>
            <option multiple={true} value={[16, 8]}>
              16 GB 8 vCPUs
            </option>
            <option multiple={true} value={[32, 16]}>
              32 GB 16 vCPUs
            </option>
            <option multiple={true} value={[64, 32]}>
              64 GB 32 vCPUs
            </option>
          </select>
        </label>
      </p>
    );
  }
}

class PublishForm extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      name: "",
      description: "",
      package_defaults: "",
      parse_user_adjustments: "",
      run_simulation: "",
      installation: "",
      server_ram: 4,
      server_cpu: 2,
      exp_task_time: 0,
      preview: this.props.preview
    };

    this.handleChange = this.handleChange.bind(this);
    this.handleServerSizeChange = this.handleServerSizeChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.togglePreview = this.togglePreview.bind(this);
    this.componentDidMount = this.componentDidMount.bind(this);
  }

  handleChange(event) {
    this.setState({ [event.target.name]: event.target.value });
  }

  handleServerSizeChange(ram, cpu) {
    this.setState({
      server_ram: ram,
      server_cpu: cpu
    });
  }

  togglePreview() {
    event.preventDefault();
    console.log(this.state.preview);
    this.setState({ preview: !this.state.preview });
  }

  componentDidMount() {
    this.props.fetch_init_state().then(data => {
      this.setState(data);
    });
  }

  handleSubmit(event) {
    event.preventDefault();
    this.props.fetch_on_submit(this.state);
  }

  render() {
    return (
      <form onSubmit={this.handleSubmit}>
        <h3>About</h3>
        <hr className="my-4" />
        <TextField
          handleChange={this.handleChange}
          label="App Name"
          name="name"
          value={this.state.name}
          type="text"
          placeholder="What's the name of this app?"
          preview={this.state.preview}
        />
        <Description
          handleChange={this.handleChange}
          description={this.state.description}
          preview={this.state.preview}
        />
        <h3>Python Functions</h3>
        <hr className="my-4" />
        <p>
          <em>
            Insert code snippets satisfying the requirements detailed in the{" "}
            <a href="https://github.com/comp-org/comp/blob/master/docs/ENDPOINTS.md">
              functions documentation.
            </a>
          </em>
        </p>
        <CodeSnippet
          handleChange={this.handleChange}
          function_name="Get package defaults"
          name="package_defaults"
          description="Get the default Model Parameters and their meta data"
          code={this.state.package_defaults}
          preview={this.state.preview}
          language="python"
        />
        <CodeSnippet
          handleChange={this.handleChange}
          function_name="Parse user adjustments"
          name="parse_user_adjustments"
          description="Do model-specific formatting and validation on the user adjustments"
          code={this.state.parse_user_adjustments}
          preview={this.state.preview}
          language="python"
        />
        <CodeSnippet
          handleChange={this.handleChange}
          function_name="Run simulation"
          name="run_simulation"
          description="Submit the user adjustments (or none) to the model to run the simulations"
          code={this.state.run_simulation}
          preview={this.state.preview}
          language="python"
        />
        <h3>Environment</h3>
        <hr className="my-4" />
        <p>
          <em>
            Describe how to install this project and its resource requirements
            as detailed in{" "}
            <a href="/comp-org/comp/blob/master/docs/ENVIRONMENT.md">
              the environment documentation.
            </a>
          </em>
        </p>
        <CodeSnippet
          handleChange={this.handleChange}
          function_name="Installation"
          name="installation"
          description="Bash commands for installing this project"
          code={this.state.installation}
          preview={this.state.preview}
          language="bash"
        />
        <ServerSize
          handleServerSizeChange={this.handleServerSizeChange}
          server_ram={this.state.server_ram}
          server_cpu={this.state.server_cpu}
        />
        <TextField
          handleChange={this.handleChange}
          label="Expected time in seconds for simulation completion"
          name="exp_task_time"
          value={this.state.exp_task_time}
          type="number"
          preview={false}
        />
        <button className="btn inline-block" onClick={this.togglePreview} value>
          {this.state.preview ? "Edit" : "Preview"}
        </button>
        <div class="divider" />
        <input
          className="btn inline-block go-btn"
          type="submit"
          value={this.props.submitType}
        />
      </form>
    );
  }
}

class AppDetail extends React.Component {
  constructor(props) {
    super(props);
    this.fetch_init_state = this.fetch_init_state.bind(this);
    this.fetch_on_submit = this.fetch_on_submit.bind(this);
  }

  fetch_init_state() {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    return axios
      .get(`/publish/api/${username}/${app_name}/detail/`)
      .then(function(response) {
        console.log(response);
        return response.data;
      })
      .catch(function(error) {
        console.log(error);
      });
  }

  fetch_on_submit(data) {
    const username = this.props.match.params.username;
    const app_name = this.props.match.params.app_name;
    axios
      .put(`/publish/api/${username}/${app_name}/detail/`, data)
      .then(function(response) {
        console.log(response);
        window.location.replace(`/${username}/`);
      })
      .catch(function(error) {
        console.log(error);
      });
  }

  render() {
    return (
      <PublishForm
        fetch_init_state={this.fetch_init_state}
        fetch_on_submit={this.fetch_on_submit}
        preview={true}
        submitType="Update"
      />
    );
  }
}

class CreateApp extends React.Component {
  constructor(props) {
    super(props);
    this.fetch_init_state = this.fetch_init_state.bind(this);
    this.fetch_on_submit = this.fetch_on_submit.bind(this);
  }
  fetch_init_state() {
    return new Promise(() => {});
  }
  fetch_on_submit(data) {
    axios
      .post("/publish/", data)
      .then(function(response) {
        console.log(response);
        window.location.replace(response.url);
      })
      .catch(function(error) {
        console.log(error);
      });
  }
  render() {
    return (
      <PublishForm
        fetch_init_state={this.fetch_init_state}
        fetch_on_submit={this.fetch_on_submit}
        preview={false}
        submitType="Publish"
      />
    );
  }
}

const domContainer = document.querySelector("#publish-container");

ReactDOM.render(
  <BrowserRouter>
    <Switch>
      <Route exact path="/publish/" component={CreateApp} />
      <Route path="/:username/:app_name/detail/" component={AppDetail} />
    </Switch>
  </BrowserRouter>,
  domContainer
);
