function is_assignment(line, key, pattern) {
  pattern = "^[[:space:]]*(export[[:space:]]+)?" key "[[:space:]]*[=:]"
  return line ~ pattern
}

function assignment_value(line, key, value, pattern) {
  pattern = "^[[:space:]]*(export[[:space:]]+)?" key "[[:space:]]*[=:]"
  value = line
  sub(pattern, "", value)
  return value
}

function has_unclosed_single_quote(line, value, i, character, pattern) {
  pattern = "^[[:space:]]*(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*[[:space:]]*[=:]"
  if (line !~ pattern) return 0

  value = line
  sub(pattern, "", value)
  sub(/^[[:space:]]+/, "", value)
  if (substr(value, 1, 1) != "'") return 0

  for (i = 2; i <= length(value); i++) {
    character = substr(value, i, 1)
    if (character == "\\") {
      i++
    } else if (character == "'") {
      return 0
    }
  }
  return 1
}

function closes_single_quote(line, i, character) {
  for (i = 1; i <= length(line); i++) {
    character = substr(line, i, 1)
    if (character == "\\") {
      i++
    } else if (character == "'") {
      return 1
    }
  }
  return 0
}

function update_quote_state(line) {
  if (in_single_quote) {
    if (closes_single_quote(line)) {
      in_single_quote = 0
      skip_multiline = 0
    }
  } else if (has_unclosed_single_quote(line)) {
    in_single_quote = 1
  }
}

function normalized_project_value(line, value) {
  value = assignment_value(line, "COMPOSE_PROJECT_NAME")
  sub(/^[[:space:]]+/, "", value)
  sub(/^#.*/, "", value)
  sub(/[[:space:]]+#.*$/, "", value)
  sub(/[[:space:]]+$/, "", value)

  if (substr(value, 1, 1) == "'" && substr(value, length(value), 1) == "'") {
    value = substr(value, 2, length(value) - 2)
  } else if (substr(value, 1, 1) == "\"" && substr(value, length(value), 1) == "\"") {
    value = substr(value, 2, length(value) - 2)
  }
  return value
}

{
  line = $0

  if (in_single_quote) {
    if ((MODE == "probe" || MODE == "update") && !skip_multiline) print line
    else if (MODE != "probe" && MODE != "update" && MODE != "detect") print line
    update_quote_state(line)
    next
  }

  project_assignment = is_assignment(line, "COMPOSE_PROJECT_NAME")

  if (MODE == "detect") {
    if (project_assignment) configured = normalized_project_value(line) != ""
    update_quote_state(line)
    next
  }

  if (MODE == "probe" && project_assignment) {
    print "COMPOSE_PROJECT_NAME="
    skip_multiline = has_unclosed_single_quote(line)
    if (skip_multiline) in_single_quote = 1
    next
  }

  if (MODE == "update" && project_assignment) {
    project_seen = 1
    if (update_project == "yes") {
      print "COMPOSE_PROJECT_NAME=" project_name
      skip_multiline = has_unclosed_single_quote(line)
      if (skip_multiline) in_single_quote = 1
    } else {
      print line
      update_quote_state(line)
    }
    next
  }

  if (MODE == "update" && is_assignment(line, "POSTGRES_PASSWORD")) {
    if (update_password == "yes") {
      print "POSTGRES_PASSWORD=" postgres_password
      skip_multiline = has_unclosed_single_quote(line)
      if (skip_multiline) in_single_quote = 1
    } else {
      print line
      update_quote_state(line)
    }
    password_seen = 1
    next
  }

  print line
  update_quote_state(line)
}

END {
  if (MODE == "detect") {
    print configured ? "yes" : "no"
  } else if (MODE == "update") {
    if (!project_seen && update_project == "yes") print "COMPOSE_PROJECT_NAME=" project_name
    if (!password_seen && update_password == "yes") print "POSTGRES_PASSWORD=" postgres_password
  }
}
