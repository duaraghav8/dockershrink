# DockerShrink

[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/duaraghav8)

[Talk to us on Slack](https://join.slack.com/t/dockershrink/shared_invite/zt-2vwkeqw0k-JXmHBNCQnG4X1BBf1t3xyg) **|** [Vote for Feature Requests](https://github.com/duaraghav8/dockershrink/issues?q=is%3Aopen+is%3Aissue+label%3Afeature-request)

---

Dockershrink is an AI-powered Commandline Tool that helps you reduce the size of your Docker images

![Typical interaction with dockershrink CLI](./assets/images/dockershrink-how-it-works.gif)

It combines the power of algorithmic analysis with Generative AI to apply state-of-the-art optimizations to your Image configurations :brain:

Dockershrink can automatically apply techniques like Multi-Stage builds, switching to Lighter base images like alpine and running dependency checks. PLUS a lot more is on the roadmap :rocket:

Currently, the tool only supports [NodeJS](https://nodejs.org/en) applications.

It can:

1. **Generate** optimized Docker image defintions (Dockerfile and .dockerignore) for new projects
2. **Optimize** existing image definition by including best practices to avoid bloat

> [!IMPORTANT]
> Dockershrink is **BETA** software.
>
> You can provide your feedback by [creating an Issue](https://github.com/duaraghav8/dockershrink/issues) in this repository.

## Why does dockershrink exist?

Every org using containers in development or production environments understands the pain of managing hundreds or even thousands of bloated Docker images in their infrastructure.

High data storage and transfer costs, long build times, underprodctive developers - we've seen it all.

The issue becomes even more painful and costly with interpreted languages such as Nodejs & Python.
Apps written in these languages need to pack the interpreters and all their dependencies inside their container images, significantly increasing their size.

But not everyone realizes that by just implementing some basic techniques, they can reduce the size of a 1GB Docker image down to **as little as 100 MB**!

([I also made a video on how to do this.](https://youtu.be/vHBHxQfK6cM))

Imagine the costs saved in storage & data transfer, decrease in build times AND the productivity gains for developers :exploding_head:

Dockershrink aims to automatically apply advanced optimization techniques so engineers don't have to waste time on it and the organization still saves :moneybag:!

You're welcome :wink:

## Installation

Dockershrink is shipped as a stand-alone binary.

You can either download it from the [Releases](https://github.com/duaraghav8/dockershrink/releases) Page or use [Homebrew](https://brew.sh/) to install it:

```bash
$ brew install duaraghav8/tap/dockershrink
```

> [!IMPORTANT]
> On MacOS, you will have to use homebrew because the compiled binary is not [Notarized](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).

## Usage

Navigate into the root directory of your Node.js project and invoke dockershrink:

```bash
# To optimize existing Docker-related files
$ dockershrink optimize

# To generate new Docker files
$ export DOCKERSHRINK_API_KEY=...
$ dockershrink generate
```

Dockershrink creates a new directory which contains the files produced by it.
By default, this directory is `dockershrink.out`.

For detailed information about a command, run

```bash
$ dockershrink help optimize
$ dockershrink help generate
```

You can also use the `--debug` option to get DEBUG logs. These are especially helpful during troubleshooting.

```bash
$ dockershrink generate --debug
```

### Using AI Features

> [!NOTE]
> Using AI features is optional for "optimize" (but highly recommended) and mandatory for "generate".

Dockershrink can use **any OpenAI-compatible API endpoint** for its AI features. This includes OpenAI, Anthropic, and AWS Bedrock.

If you want to enable AI, you must supply your API key and (optionally) a custom base URL for your chosen endpoint.

Requests will be sent to [OpenAI's API](https://openai.com/index/openai-api/) by default, if no base URL is provided.

So even though Dockershrink itself is free, LLM usage might incur some cost for you.

```bash
dockershrink optimize --api-key <your endpoint's api key> --base-url <your endpoint's base url>
```

Or set them as environment variables:

```bash
export DOCKERSHRINK_API_KEY="<your endpoints api key>"
export DOCKERSHRINK_BASE_URL="<your endpoints base url>"
dockershrink generate
```

**Examples:**

- **OpenAI (default):**

  ```bash
  export DOCKERSHRINK_API_KEY="<your OpenAI API key>"
  dockershrink generate
  ```

- **AWS Bedrock:**

  ```bash
  export DOCKERSHRINK_API_KEY="<your bedrock key>"
  export DOCKERSHRINK_BASE_URL="http://your-bedrock-endpoint"
  dockershrink generate
  ```

- **Ollama:**
  ```bash
  # Assumes you are running a model that [supports tool calling](https://ollama.com/blog/tool-support) locally with Ollama
  dockershrink optimize --api-key 'ollama' --model "llama3.1"
  ```

> [!NOTE]
> Dockershrink does not store your provided API Key.
>
> So you must provide your key every time you want Dockershrink to use it.
> This is to avoid any unexpected costs.

---

## Development :computer:

> [!NOTE]
> This section is for authors and contributors.
> If you're simply interested in using Dockershrink, you can skip it.

### Prerequisites

- Clone this repository on to your local machine.
- Make sure [Golang](https://golang.org/dl/) is installed on your system (at least version 1.23)
- Make sure [Docker](https://www.docker.com/get-started) installed on your system and the Docker daemon is running.
- Install [GoReleaser](https://goreleaser.com/) (at least version 2.4)

### Development

1. After cloning this repository, navigate inside the root directory of the project
2. Run tests to ensure everything is working

```bash
go test ./...
```

3. Make your code changes, add relevant tests.
4. Tidy up and make sure all tests pass

```bash
go mod tidy
go mod vendor
go test ./...
```

### Build for local testing

```bash
# Single binary
goreleaser build --single-target --clean --snapshot

# All binaries
goreleaser release --snapshot --clean
```

### Create a new release

1. Create a Git Tag with the new version

```bash
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0
```

2. Release

```bash
# Make sure GPG is present on your system and you have a default key which is added to Github.

# set your github access token
export GITHUB_TOKEN="<your GH token>"

goreleaser release --clean
```

This will create a new release under Releases and also make it available via Homebrew.
