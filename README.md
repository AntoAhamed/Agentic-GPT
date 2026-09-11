# AgenticGPT

AgenticGPT is a Streamlit-powered AI assistant that combines LangGraph orchestration, Gemini LLMs, and retrieval-augmented generation (RAG) to help users ask questions, search the web, calculate results, check weather, and query PDFs uploaded within each conversation.

## Features

- Chat-based AI interface built with Streamlit
- Persistent conversation history using SQLite-backed LangGraph checkpoints
- PDF ingestion and retrieval for conversation-specific knowledge bases
- Web search through Tavily
- Weather lookup through WeatherAPI
- Calculator tool for math expressions
- Per-thread FAISS vector stores for isolated document memory
- Multi-turn agent execution with tool-calling and LangGraph

## Tech Stack

- Python
- Streamlit
- LangGraph
- LangChain
- Google Gemini
- FAISS
- Tavily Search
- SQLite
- PyPDF

## Project Structure

```text
AgenticGPT/
├── app.py                 # Streamlit frontend and UI logic
├── backend.py            # LangGraph agent, tools, and RAG setup
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (not included in repo)
├── agenticgpt.db         # SQLite checkpoint database
├── faiss_db/             # Per-thread FAISS indexes
├── uploaded_pdfs/        # Uploaded PDF files stored by thread
├── LICENSE               # Project license
└── README.md             # Project documentation
```

## How It Works

1. The user interacts with the Streamlit app in `app.py`.
2. The backend agent in `backend.py` uses LangGraph to orchestrate the conversation.
3. Gemini is used as the main language model.
4. Tools can be invoked when needed:
   - `rag_tool` for PDF-based retrieval
   - `search_tool` for web search
   - `get_weather_data` for weather queries
   - `calculator` for math operations
5. Each conversation thread has its own FAISS vector store and uploaded PDFs, so document context is isolated by chat.

## Prerequisites

- Python 3.10+ recommended
- A Google Gemini API key
- A Tavily API key
- A WeatherAPI key
- Conda or a virtual environment (optional but recommended)

## Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd AgenticGPT
```

### 2. Create and activate a virtual environment

Using Conda:

```bash
conda create -n agenticgpt python=3.10 -y
conda activate agenticgpt
```

Or using venv:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root with the following values:

```env
GEMINI_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
WEATHERAPI_API_KEY=your_weatherapi_key
```

> If you do not provide `WEATHERAPI_API_KEY`, the weather tool will not work correctly.

### 5. Run the app

```bash
streamlit run app.py
```

Then open the local URL shown by Streamlit in your browser.

## Usage

### Ask general questions

Use the chat input to ask the assistant questions that can be answered from its language model knowledge and available tools.

### Search the web

Ask for current information, recent events, or general web lookups. The assistant can use the Tavily search tool when needed.

### Upload a PDF

You can upload a PDF in the chat input. The app will:

- save the file in `uploaded_pdfs/<thread_id>/`
- split and index the PDF content via FAISS
- make it available as retrieval context for that conversation only

Then ask questions about the document content.

### Use the calculator

Ask the assistant to perform mathematical tasks like:

- `What is 12 * 8?`
- `Calculate sqrt(144)`
- `Evaluate 3^4 + 10`

### Check the weather

Ask for weather information for a city, for example:

- `What is the weather in London?`
- `Check the weather in Tokyo`

## Conversation Behavior

- Each chat is tracked by a generated thread ID.
- Conversation history and tool state are stored with SQLite checkpoints.
- Uploaded PDFs and FAISS indexes are stored per thread, which keeps documents isolated between chats.

## Notes

- The backend currently excludes email and WhatsApp tools in order to keep the project suitable for free deployment environments such as Render.
- The app is intended as a learning/demo project and can be extended with additional tools or a custom frontend.

## License

This project is distributed under the license included in the repository. See `LICENSE` for details.

## Troubleshooting

### Missing API keys

If the assistant fails to use tools or responds with missing configuration errors, check that your `.env` file contains all required keys.

### PDF indexing issues

If a PDF does not seem to be available for retrieval:

- confirm the file uploaded successfully
- check that `uploaded_pdfs/<thread_id>/` contains the file
- confirm the app has permission to write to the workspace

### Dependency issues

If installation fails, try upgrading pip first:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Future Improvements

Possible enhancements include:

- improving prompt design and tool routing
- adding support for more document formats
- enabling user authentication
- deploying the app to cloud hosting
- adding additional agent actions and guardrails
