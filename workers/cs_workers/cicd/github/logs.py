def parse_logs(logs):
    lines = []
    # strip timestamps
    for line in logs.split("\r\n"):
        pieces = line.split("Z")
        lines.append(("Z".join(pieces[1:])).strip())
    logs = "\r\n".join(lines)

    # essentially logs are structured as:
    # ##[group]
    # sometimes a command
    # metadata about command from github
    # ##[endgroup]
    # output from command
    # ...
    # ##[group]
    place = 0
    cmds = {
        "cs workers models build": "build",
        "cs workers models test": "test",
        "cs workers models push": "push",
    }
    outputs = []
    while place < len(logs) and place > -1:
        section_start = logs.find("##[group]", place)
        section_end = logs.find("##[endgroup]", section_start)
        section = logs[section_start:section_end].replace("##[group]", "")
        maybe_command = section.split("\r\n")[0].replace("Run ", "")
        if maybe_command in cmds:
            next_group = logs.find("##[group]", section_end)
            cmd_logs = (
                logs[section_end:next_group]
                .replace("##[endgroup]", "")
                .replace("\r\n", "\n")
                .strip()
            )
            outputs.append(
                {
                    "cmd": maybe_command,
                    "logs": cmd_logs,
                    "stage": cmds.get(maybe_command),
                }
            )

        place = section_end

    return outputs
