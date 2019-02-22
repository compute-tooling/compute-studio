"use strict";

const e = React.createElement;

const csrftoken = Cookies.get("csrftoken");

class Description extends React.Component {
  constructor(props) {
    super(props);
    this.handleChange = this.handleChange.bind(this);
  }

  handleChange(event) {
    this.props.handleDescriptionChange(event.target.value);
  }

  render() {
    const description = this.props.description;
    const charsLeft = 1000 - description.length;
    return (
      <p className="description">
        <label>
          <b>App overview:</b>
          <textarea
            className="form-control"
            name="description"
            type="text"
            placeholder="What does this app do? Must be less than 1000 characters."
            value={description}
            onChange={this.handleChange}
            maxLength="1000"
            style={{ width: "50rem" }}
            // required - shows up red before entering text on firefox?
          />
        </label>
        <small>{charsLeft}</small>
      </p>
    );
  }
}

class CodeSnippet extends React.Component {
  constructor(props) {
    super(props);
    this.handleChange = this.handleChange.bind(this);
  }

  handleChange(event) {
    this.props.handleCodeSnippetChange(this.props.name, event.target.value);
  }

  render() {
    return (
      <p>
        <label>
          <b>{this.props.function_name + ":"}</b> {this.props.description}
          <textarea
            className="form-control"
            name={this.props.name}
            type="text"
            placeholder="# code snippet here"
            value={this.props.code}
            onChange={this.handleChange}
            style={{ width: "50rem" }}
            // required - shows up red before entering text on firefox?
          />
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
    console.log(event.target.value);
    this.props.handleServerSizeChange(cpu, ram);
  }

  render() {
    return (
      <p>
        <label>
          Choose the server size:
          <select name="server_size" onChange={this.handleChange}>
            <option multiple={true} value={[4, 2]}>
              {" "}
              4 GB 2 vCPUs{" "}
            </option>
            <option multiple={true} value={[8, 4]}>
              {" "}
              8 GB 4 vCPUs{" "}
            </option>
            <option multiple={true} value={[16, 8]}>
              16 GB 8 vCPUs
            </option>
            <option multiple={true} value={[32, 16]}>
              32 GB 16 vCPUs
            </option>
            <option multiple={true} value={[64, 32]}>
              {" "}
              64 GB 32 vCPUs{" "}
            </option>
          </select>
        </label>
      </p>
    );
  }
}

class Publish extends React.Component {
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
      exp_task_time: 0
    };

    this.handleChange = this.handleChange.bind(this);
    this.handleDescriptionChange = this.handleDescriptionChange.bind(this);
    this.handleCodeSnippetChange = this.handleCodeSnippetChange.bind(this);
    this.handleServerSizeChange = this.handleServerSizeChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
  }

  handleChange(event) {
    console.log(event.target.name);
    console.log(event.target.value);
    this.setState({ [event.target.name]: event.target.value });
  }

  handleDescriptionChange(description) {
    this.setState({ description: description });
  }

  handleCodeSnippetChange(name, code) {
    this.setState({ [name]: code });
  }

  handleServerSizeChange(ram, cpu) {
    this.setState({
      server_ram: ram,
      server_cpu: cpu
    });
  }

  handleSubmit(event) {
    event.preventDefault();
    let data = new FormData(event.target);
    data.set("csrfmiddlewaretoken", csrftoken);
    data.set("name", this.state.name);
    data.set("description", this.state.description);
    data.set("package_defaults", this.state.package_defaults);
    data.set("parse_user_adjustments", this.state.parse_user_adjustments);
    data.set("run_simulation", this.state.run_simulation);
    data.set("installation", this.state.installation);
    data.set("server_ram", this.state.server_ram);
    data.set("server_cpu", this.state.server_cpu);
    data.set("exp_task_time", this.state.exp_task_time);
    response = fetch("/publish/", {
      method: "POST",
      body: data,
      credentials: "same-origin"
    }).then(function(response) {
      window.location.replace(response.url);
    });
  }

  render() {
    return (
      <form onSubmit={this.handleSubmit}>
        <h3>About</h3>
        <hr className="my-4" />
        <p>
          <label>
            <b>App Name:</b>
            <input
              className="form-control"
              name="name"
              type="text"
              value={this.state.name}
              placeholder="What's the name of the app?"
              onChange={this.handleChange}
              required
            />
          </label>
        </p>
        <Description
          handleDescriptionChange={this.handleDescriptionChange}
          description={this.state.description}
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
          handleCodeSnippetChange={this.handleCodeSnippetChange}
          function_name="Get package defaults"
          name="package_defaults"
          description="Get the default Model Parameters and their meta data"
          code={this.state.package_defaults}
        />
        <CodeSnippet
          handleCodeSnippetChange={this.handleCodeSnippetChange}
          function_name="Parse user adjustments"
          name="parse_user_adjustments"
          description="Do model-specific formatting and validation on the user adjustments"
          code={this.state.parse_user_adjustments}
        />
        <CodeSnippet
          handleCodeSnippetChange={this.handleCodeSnippetChange}
          function_name="Run simulation"
          name="run_simulation"
          description="Submit the user adjustments (or none) to the model to run the simulations"
          code={this.state.run_simulation}
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
          handleCodeSnippetChange={this.handleCodeSnippetChange}
          function_name="Installation"
          name="installation"
          description="Bash commands for installing this project"
          code={this.state.installation}
        />
        <ServerSize
          handleServerSizeChange={this.handleServerSizeChange}
          server_ram={this.state.server_ram}
          server_cpu={this.state.server_cpu}
        />
        <p>
          <label>
            <b>Expected time in seconds for simulation completion:</b>
            <input
              className="form-control"
              name="exp_task_time"
              type="number"
              value={this.state.exp_task_time}
              // placeholder=
              onChange={this.handleChange}
              required
            />
          </label>
        </p>
        <input type="submit" value="Submit" />
      </form>
    );
  }
}

const domContainer = document.querySelector("#publish-container");
ReactDOM.render(e(Publish), domContainer);
