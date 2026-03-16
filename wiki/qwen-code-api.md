# `Qwen Code` API

<h2>Table of contents</h2>

- [What is `Qwen Code` API](#what-is-qwen-code-api)
- [Set up the `Qwen Code` API (REMOTE)](#set-up-the-qwen-code-api-remote)
  - [Set up the `Qwen Code` CLI (REMOTE)](#set-up-the-qwen-code-cli-remote)
  - [Start the `Qwen Code` API service (REMOTE)](#start-the-qwen-code-api-service-remote)
  - [Get the `Qwen Code` API config values (REMOTE)](#get-the-qwen-code-api-config-values-remote)
  - [Check that the `Qwen Code` API is accessible (REMOTE or LOCAL)](#check-that-the-qwen-code-api-is-accessible-remote-or-local)

## What is `Qwen Code` API

<!-- TODO visualize -->

[`qwen-code-oai-proxy`](https://github.com/inno-se-toolkit/qwen-code-oai-proxy) exposes [`Qwen Code`](./qwen.md#what-is-qwen-code) through an [OpenAI-compatible API](./llm.md#openai-compatible-api) so that other tools can use it as an [LLM](./llm.md#what-is-an-llm).

See:

- [Set up the `Qwen Code` API (REMOTE)](#set-up-the-qwen-code-api-remote)

## Set up the `Qwen Code` API (REMOTE)

Complete these steps:

1. [Set up the `Qwen Code` CLI (REMOTE)](#set-up-the-qwen-code-cli-remote).
2. [Start the `Qwen Code` API service (REMOTE)](#start-the-qwen-code-api-service-remote).
3. [Get the `Qwen Code` API config values (REMOTE)](#get-the-qwen-code-api-config-values-remote).
4. [Check that the `Qwen Code` API is accessible (REMOTE)](#check-that-the-qwen-code-api-is-accessible-remote-or-local).
5. [Check that the `Qwen Code` API is accessible (LOCAL)](#check-that-the-qwen-code-api-is-accessible-remote-or-local).

### Set up the `Qwen Code` CLI (REMOTE)

1. [Connect to the VM](./ssh.md#connect-to-the-vm).

2. [Install `Node.js`](./nodejs.md#install-nodejs).

3. [Install `pnpm`](./nodejs.md#install-pnpm).

4. To install [`Qwen Code`](./qwen.md#what-is-qwen-code),

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   pnpm add -g @qwen-code/qwen-code
   ```

5. [Open a chat with `Qwen Code` using the CLI](./qwen.md#open-a-chat-with-qwen-code-using-the-cli).

6. Write `/auth` in the chat to [authenticate via Qwen OAuth](https://github.com/QwenLM/qwen-code?tab=readme-ov-file#authentication).

7. Open the link in a browser to complete the authentication procedure.

8. [Quit the chat with `Qwen Code`](./qwen.md#quit-the-chat-with-qwen-code).

### Start the `Qwen Code` API service (REMOTE)

1. To [clone using the `VS Code Terminal` the repo](./git-vscode.md#clone-the-repo-using-the-vs-code-terminal)

   <https://github.com/inno-se-toolkit/qwen-code-oai-proxy>,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   git clone https://github.com/inno-se-toolkit/qwen-code-oai-proxy ~/qwen-code-oai-proxy
   ```

2. To enter the repository directory,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cd ~/qwen-code-oai-proxy
   ```

3. To create the [environment](./environments.md#what-is-an-environment) file,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cp .env.example .env
   ```

4. To open the `.env` file in `nano`,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   nano .env
   ```

5. Write an arbitrary value for `QWEN_API_KEY`.

   This key will protect your `Qwen Code` API.

6. Save the file (`Ctrl + O`).

7. To start the `Qwen Code` API,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   docker compose up --build -d
   ```

### Get the `Qwen Code` API config values (REMOTE)

1. [Connect to your VM](./vm.md#connect-to-the-vm) if not yet connected.

2. To enter the `Qwen Code` API repository directory,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cd ~/qwen-code-oai-proxy
   ```

3. To get the value of `HOST_PORT` in `.env`,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cat .env | grep HOST_PORT
   ```

4. To get the value of `QWEN_API_KEY` in `.env`,

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   cat .env | grep QWEN_API_KEY
   ```

### Check that the `Qwen Code` API is accessible (REMOTE or LOCAL)

1. [Get the `Qwen Code` API config values (REMOTE)](#get-the-qwen-code-api-config-values-remote):

   - `HOST_PORT`
   - `QWEN_API_KEY`.

2. To send the request to the `Qwen Code` API (REMOTE or LOCAL),

   [run in the `VS Code Terminal`](./vs-code.md#run-a-command-in-the-vs-code-terminal):

   ```terminal
   curl -s http://<qwen-code-api-address>:<qwen-api-port>/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <qwen-api-key>" \
     -d '{"model":"<qwen-model>","messages":[{"role":"user","content":"What is 2+2?"}]}' \
     | jq .
   ```

   Replace placeholders:

   - `<qwen-code-api-address>` with:
     - `localhost` if you run on your VM (REMOTE)
     - [`<your-vm-ip-address>`](vm.md#your-vm-ip-address) if you run on your laptop (LOCAL)
   - `<qwen-api-port>` with the value of `HOST_PORT`
   - `<qwen-api-key>` with the value of `QWEN_API_KEY`
   - `<qwen-model>` with one of the available models:

     - `coder-model` — `Qwen 3.5 Plus` (recommended).
     - `qwen3-coder-plus` — `Qwen 3 Coder Plus`.
     - `qwen3-coder-flash` — `Qwen 3 Coder Flash` (faster).

3. When you run it, the output should be similar to this:

   ```terminal
   {
      "created": 1773379590,
      "usage": {
         "completion_tokens": 8,
         "prompt_tokens": 15,
         "prompt_tokens_details": {
            "cached_tokens": 0
         },
         "total_tokens": 23
      },
      "model": "qwen3-coder-plus",
      "id": "chatcmpl-9c04fd89-7d16-469f-af7b-8e64a9418bb3",
      "choices": [
         {
            "finish_reason": "stop",
            "index": 0,
            "message": {
            "role": "assistant",
            "content": "2 + 2 = 4."
            }
         }
      ],
      "object": "chat.completion"
   }
   ```
