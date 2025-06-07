# `ctlmind`

An LLM assistant for systemd investigation and administration. This tool
provides a chat interface to interact with an AI assistant that can help you
with systemd-related tasks.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your OpenAI API key as an environment variable:
   ```bash
   export OPENAI_API_KEY='your-api-key'
   ```

## Usage

Run the chat interface:
```bash
python main.py
```

You can then start asking questions about systemd. Type `exit` or `quit` to end
the chat.