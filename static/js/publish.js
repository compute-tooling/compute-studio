'use strict';

const e = React.createElement;

const csrftoken = Cookies.get('csrftoken');

class Description extends React.Component {
  constructor(props) {
    super(props);
    this.handleChange = this.handleChange.bind(this);
  }

  handleChange(event) {
    this.props.handleDescriptionChange(event.target.value);
  }

  render() {
    const description = this.props.app_description;
    const charsLeft = 1000 - description.length;
    return (
      <p className="description">
      <label>
        <b>App overview:</b>
        <textarea
          className="form-control"
          name="app_description"
          type="text"
          placeholder="What does this app do? Must be less than 1000 characters."
          value={description}
          onChange={this.handleChange}
          maxLength="1000"
          style={{width: "50rem"}}
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

  render () {
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
            style={{width: "50rem"}}
            // required - shows up red before entering text on firefox?
          />
        </label>
      </p>
    );
  }
}

class Publish extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      app_name: '',
      app_description: '',
      package_defaults: '',
      parse_user_adjustments: '',
      run_simulation: '',
      install: '',
      server_size: '',
    };

    this.handleChange = this.handleChange.bind(this);
    this.handleDescriptionChange = this.handleDescriptionChange.bind(this);
    this.handleCodeSnippetChange = this.handleCodeSnippetChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
  }

  handleChange(event) {
    const target = event.target;
    const value = target.value;
    const name = target.name
    this.setState({[name]: value});
  }

  handleDescriptionChange(description) {
    this.setState({app_description: description});
  }

  handleCodeSnippetChange(name, code) {
    this.setState({[name]: code})
  }

  handleSubmit(event) {
    event.preventDefault();
    let data = new FormData(event.target);
    data.set("csrfmiddlewaretoken", csrftoken);
    data.set("app_name", this.state.app_name);
    data.set("app_description", this.state.app_description);
    data.set("package_defaults", this.state.package_defaults);
    data.set("parse_user_adjustments", this.state.parse_user_adjustments);
    data.set("run_simulation", this.state.run_simulation);
    data.set("install", this.state.install);
    data.set("server_size", this.state.server_size);

    fetch('/publish/', {
      method: 'POST',
      body: data,
      credentials: 'same-origin',
    });
  }

  render() {
    return (
      <form onSubmit={this.handleSubmit}>
        <h3>About</h3>
        <hr className="my-4"/>
        <p>
          <label>
            <b>App Name:</b>
            <input
              className="form-control"
              name="app_name"
              type="text"
              value={this.state.app_name}
              placeholder="What's the name of the app?"
              onChange={this.handleChange}
              required
            />
          </label>
        </p>
        <Description
          handleDescriptionChange={this.handleDescriptionChange}
          app_description={this.state.app_description}/>
        <h3>Python Functions</h3>
        <hr className="my-4"/>
        <p><em>Insert code snippets satisfying the requirements detailed in the <a href="https://github.com/comp-org/comp/blob/master/docs/ENDPOINTS.md">functions documentation.</a></em></p>
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
        <hr className="my-4"/>
        <p><em>Describe how to install this project and its resource requirements as detailed in <a href="/comp-org/comp/blob/master/docs/ENVIRONMENT.md">the environment documentation.</a></em></p>
        <CodeSnippet
          handleCodeSnippetChange={this.handleCodeSnippetChange}
          function_name="Installation"
          name="install"
          description="Bash commands for installing this project"
          code={this.state.install}
        />
        <p>
        <label>
          Choose the server size:
          <select value={this.state.server_size} onChange={this.handleChange}>
            <option value=" 4 GB 	2 vCPUs "> 4 GB 	2 vCPUs </option>
            <option value=" 8 GB 	4 vCPUs "> 8 GB 	4 vCPUs </option>
            <option value="16 GB 	8 vCPUs">16 GB 	8 vCPUs</option>
            <option value="32 GB 	16 vCPUs">32 GB 	16 vCPUs</option>
            <option value=" 64 GB 	32 vCPUs "> 64 GB 	32 vCPUs </option>
          </select>
        </label>
        </p>
        <input type="submit" value="Submit" />
      </form>
    );
  }
}

const domContainer = document.querySelector('#publish-container');
ReactDOM.render(e(Publish), domContainer);
