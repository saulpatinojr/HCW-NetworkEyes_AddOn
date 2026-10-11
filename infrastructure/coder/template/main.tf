# Coder template: per-user, time-limited Docker workspace preloaded with one Network Assessment bundle.
# Security: no privileged mode, no Docker socket in the workspace, no enterprise network, no production credentials.
terraform {
  required_providers {
    coder  = { source = "coder/coder", version = "~> 2.4" }
    docker = { source = "kreuzwerker/docker", version = "~> 3.0" }
  }
}

variable "workspace_image" {
  type        = string
  description = "Lab workspace image (code-server, terraform, pwsh, az cli; no credentials)"
  default     = "docker.io/hybridcloudworks/hcw-lab:latest"
}

data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

data "coder_parameter" "assessment_id" {
  name         = "assessment_id"
  display_name = "Assessment ID"
  type         = "string"
  mutable      = false
  validation {
    regex = "^[0-9a-f-]{36}$"
    error = "must be an assessment UUID"
  }
}

data "coder_parameter" "bundle_token" {
  name         = "bundle_token"
  display_name = "One-time bundle token"
  type         = "string"
  mutable      = false
  ephemeral    = true
}

data "coder_parameter" "api_base_url" {
  name         = "api_base_url"
  display_name = "Lab API base URL"
  type         = "string"
  mutable      = false
  default      = "https://network-assessment.lab.hybridcloudworks.com"
}

resource "coder_agent" "main" {
  arch           = "amd64"
  os             = "linux"
  startup_script = <<-EOT
    set -eu
    mkdir -p ~/assessment && cd ~/assessment
    curl -fsSL -H "x-bundle-token: ${data.coder_parameter.bundle_token.value}" \
      "${data.coder_parameter.api_base_url.value}/api/assessments/${data.coder_parameter.assessment_id.value}/bundle.zip" -o bundle.zip
    unzip -o bundle.zip && rm bundle.zip
    cat > ~/assessment/START-HERE.md <<'MD'
    # Guided network assessment lab
    1. Read NOT-FOR-PRODUCTION.md and README.md.
    2. report.md: review executive summary, topology classification, and rule findings.
    3. findings.json and topology.json: inspect structured findings, observed-state facts, and VNet/peering graph.
    4. rules.json and summary.json: compare evaluated export rules against live-only unknowns.
    5. Use jq, python3, or pwsh in the terminal to filter findings by severity, category, or subscription (no cloud credentials or Azure access exist in this workspace).
    MD
    code-server --auth none --port 13337 ~/assessment >/tmp/code-server.log 2>&1 &
  EOT
  metadata {
    display_name = "CPU"
    key          = "cpu"
    script       = "coder stat cpu"
    interval     = 10
    timeout      = 1
  }
}

resource "coder_app" "code" {
  agent_id     = coder_agent.main.id
  slug         = "code"
  display_name = "VS Code"
  url          = "http://localhost:13337/?folder=/home/coder/assessment"
  icon         = "/icon/code.svg"
  subdomain    = false
  share        = "owner"
}

resource "docker_image" "workspace" {
  name = var.workspace_image
}

resource "docker_container" "workspace" {
  count        = data.coder_workspace.me.start_count
  image        = docker_image.workspace.image_id
  name         = "coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}"
  hostname     = data.coder_workspace.me.name
  command      = ["sh", "-c", coder_agent.main.init_script]
  env          = ["CODER_AGENT_TOKEN=${coder_agent.main.token}"]
  privileged   = false
  memory       = 2048
  cpu_shares   = 512
  network_mode = "bridge"
  host {
    host = "host.docker.internal"
    ip   = "host-gateway"
  }
  # No volumes: the workspace is disposable; artifacts are re-downloadable while the assessment lives.
}
