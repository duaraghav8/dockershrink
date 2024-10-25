content = """FROM ubuntu:latest AS build
WORKDIR /app

ENV foo=bar NODE_ENV=production APP_NAME="fire up bar" TESTER=fire\\ up\\ bar\\ test
ENV shell zsh

COPY . .
COPY --from=build /app/package*.json /app/dist /assets/
COPY package*.json .
COPY ["file1", "file2", "file3", "/files/"]

RUN --mount=type=cache,target=/root/.cache/\\
        --network=default\\
        --security=insecure\\
        apt-get install foobar -y &&\
        npx depcheck



RUN echo "hello world" && npx depcheck; apt-get install foo -y || echo done

RUN npm install


RUN ["echo", "hello world!"]


FROM node:slim

COPY --from /app/dist .
ENTRYPOINT ["npm", "run"]

LABEL a="value" b="valueb" c="done"

LABEL lorem="ipsum" \\
ipsum="dolor" \\
dolor="baxos"

LABEL "com.example.vendor"="ACME Incorporated"
LABEL com.example.label-with-value="foo"
LABEL version="1.0"
LABEL description="This text illustrates \\
that label-values can span multiple lines."

LABEL multi.label1="value1" multi.label2="value2" other="value3"

ENV foo=bar \\
    bar="baz" \\
    baz=bax\\ lorem\\ ipsum\\ dolor \\
    normal="abnormal"

RUN --mount=type=cache apt-get install york -t
RUN apt-get install york -t

RUN --mount=type=cache,sec=foo --security=sandbox apt-get install psycho -y && npx depcheck; npm upgrade && /scripts/provision.sh

FROM my_own:image as run_env_tester

RUN DEBIAN_FRONTEND=noninteractive NODE_ENV=production apt-get update && apt-get install -y
"""

import dockerfile
from app.service.dockerfile import Dockerfile, Image

parsed = dockerfile.parse_string(content)
#dockerfile_ast = ast.create(parsed)

df = Dockerfile(content)
build = df.get_stage_by_name("build")

df.set_stage_baseimage(build, Image("node"))
df.set_stage_baseimage(df.get_final_stage(), Image("node:alpine"))

layers = build.layers()
df.insert_after_layer(layers[5], "RUN echo lauda-lahsun && npm install --production")

layers = build.layers()
run_cmd = layers[9].shell_commands()[1]
res = df.add_option_to_shell_command(run_cmd, key="lauda", value="lahsun")

# print(res.parent_layer().parsed_statement().original)
# print(res.parent_layer().parsed_statement().value)

layers = build.layers()
run_cmd = layers[11].shell_commands()[0]
res = df.add_option_to_shell_command(run_cmd, key="lauda", value="lahsun")

layers = build.layers()
run_cmd = layers[10].shell_commands()[0]
df.add_option_to_shell_command(run_cmd, key="production", value=True)

# print(res.parent_layer().parsed_statement().original)
# print(res.parent_layer().parsed_statement().value)

# for layer in build.layers():
#     print(layer.index(), layer.text())

layers = build.layers()
new_statements = [
    "COPY package*.json .",
    "RUN npx depcheck && my-random-app",
    "COPY . .",
]
df.replace_layer_with_statements(layers[3], new_statements)

stage = df.get_stage_by_name("run_env_tester")
run_with_env = stage.layers()[0]

print(df.raw())
