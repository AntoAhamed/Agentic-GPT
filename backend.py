# Imports
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated
from dotenv import load_dotenv
import os
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from langchain.tools import tool, ToolRuntime
import requests
import math
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_tavily import TavilySearch
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langgraph.types import interrupt, Command
import smtplib
from email.message import EmailMessage
import pywhatkit


# Load environment
load_dotenv()


# Define LLM
model = "gemini-3.1-flash-lite"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
WEATHERAPI_API_KEY = os.environ.get("WEATHERAPI_API_KEY")

llm = ChatGoogleGenerativeAI(model = model, api_key = GEMINI_API_KEY)


# RAG implementation
embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")

def ingest_rag_documents(file_path, thread_id):
    """
    Add a PDF to the RAG knowledge base
    belonging only to this conversation.
    """

    base_db_path = "faiss_db"

    # Each conversation gets its own FAISS directory
    db_path = os.path.join(
        base_db_path,
        thread_id
    )

    os.makedirs(
        db_path,
        exist_ok=True
    )

    # -----------------------------------------
    # Load PDF
    # -----------------------------------------

    loader = PyPDFLoader(file_path)

    docs = loader.load()


    # -----------------------------------------
    # Split into chunks
    # -----------------------------------------

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_documents(docs)


    # -----------------------------------------
    # Add source filename to metadata
    # -----------------------------------------

    filename = os.path.basename(file_path)

    for chunk in chunks:

        chunk.metadata["source_file"] = filename


    # -----------------------------------------
    # Create or update FAISS database
    # -----------------------------------------

    index_file = os.path.join(
        db_path,
        "index.faiss"
    )

    if os.path.exists(index_file):

        # Existing conversation RAG database
        vector_store = FAISS.load_local(
            folder_path=db_path,
            embeddings=embeddings,
            allow_dangerous_deserialization=True
        )

        # Add the new PDF
        vector_store.add_documents(
            chunks
        )

    else:

        # First PDF in this conversation
        vector_store = FAISS.from_documents(
            chunks,
            embeddings
        )


    # -----------------------------------------
    # Save updated database
    # -----------------------------------------

    vector_store.save_local(
        db_path
    )


def get_retriever(thread_id):
    """
    Return a retriever for only the current conversation.
    """

    base_db_path = "faiss_db"

    db_path = os.path.join(
        base_db_path,
        thread_id
    )

    index_file = os.path.join(
        db_path,
        "index.faiss"
    )

    # No PDF has been uploaded in this conversation
    if not os.path.exists(index_file):

        return None


    vector_store = FAISS.load_local(
        folder_path=db_path,
        embeddings=embeddings,
        allow_dangerous_deserialization=True
    )


    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 4
        }
    )


    return retriever



# Create tools

# RAG tool
@tool
def rag_tool(query: str, runtime: ToolRuntime) -> str:
    """
    Search PDF documents uploaded in the current conversation.

    Only PDFs belonging to the current conversation are searched.
    """

    try:

        # -----------------------------------------
        # Get current conversation/thread ID
        # -----------------------------------------

        thread_id = runtime.state.get(
            "thread_id"
        )

        if not thread_id:

            return (
                "Unable to determine the current conversation."
            )


        # -----------------------------------------
        # Get conversation-specific retriever
        # -----------------------------------------

        retriever = get_retriever(
            thread_id
        )


        if retriever is None:

            return (
                "No PDF documents have been uploaded "
                "in this conversation."
            )


        # -----------------------------------------
        # Search documents
        # -----------------------------------------

        docs = retriever.invoke(
            query
        )


        if not docs:

            return (
                "No relevant information was found "
                "in the PDFs uploaded in this conversation."
            )


        # -----------------------------------------
        # Build results
        # -----------------------------------------

        results = []

        for i, doc in enumerate(
            docs,
            start=1
        ):

            content = doc.page_content.strip()

            source_file = doc.metadata.get(
                "source_file",
                "Unknown file"
            )


            if content:

                results.append(
                    f"--- Document Chunk {i} ---\n"
                    f"Source: {source_file}\n"
                    f"{content}"
                )


        return "\n\n".join(
            results
        )


    except Exception as e:

        return f"RAG search error: {str(e)}"

# Search tool
search_tool = TavilySearch(max_results=3, topic="general")

# Weather tool
@tool
def get_weather_data(city: str) -> str:
    """
    Fetch current weather information for a city.
    """

    url = (
        f"https://api.weatherapi.com/v1//current.json?"
        f"key={WEATHERAPI_API_KEY}&q={city}"
    )

    response = requests.get(url)

    data = response.json()

    if "current" not in data:
        return f"Could not fetch weather data for {city}"

    return (
        f"City: {city}\n"
        f"Temperature: {data['current']['temp_c']}°C\n"
        f"Weather: {data['current']['condition']['text']}\n"
        f"Humidity: {data['current']['humidity']}%"
    )

# Calculator tool
@tool
def calculator(expression: str) -> str:
    """
    Use this tool ONLY for mathematical calculations.

    The input MUST be a valid mathematical expression.

    Examples:
    - 2 + 2
    - 10 * 5
    - 100 / 4
    - math.sqrt(16)
    - math.pow(2, 3)

    Do NOT use this tool for:
    - current year
    - current date
    - time
    - weather
    - general knowledge
    - web searches
    - questions involving natural language

    If the user asks for current, recent, or up-to-date information,
    use the search tool instead.
    """

    try:
        allowed = {
            "math": math,
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum
        }

        result = eval(expression, {"__builtins__": {}}, allowed)
        return str(result)

    except Exception as e:
        return f"Calculation error: {str(e)}"

# Email tool
@tool
def send_email(
    recipient: str,
    subject: str,
    body: str
) -> str:
    """
    Send an email to a recipient.

    Use this tool when the user explicitly asks to send
    an email.

    Args:
        recipient: Email address of the recipient.
        subject: Subject of the email.
        body: Complete email body.
    """



    # HITL
    decision = interrupt(f"Do you want to send {body} to {recipient}? (yes/no)")

    if isinstance(decision, str) and decision.lower().strip() != "yes":

        return "Email sending aborted by the user."

    

    sender_email = os.environ.get(
        "EMAIL_ADDRESS"
    )

    app_password = os.environ.get(
        "EMAIL_APP_PASSWORD"
    )

    if not sender_email or not app_password:

        return (
            "Email configuration is missing. "
            "Please configure EMAIL_ADDRESS and "
            "EMAIL_APP_PASSWORD in the .env file."
        )


    try:

        # -----------------------------------------
        # Create email
        # -----------------------------------------

        message = EmailMessage()

        message["From"] = sender_email
        message["To"] = recipient
        message["Subject"] = subject

        message.set_content(
            body
        )


        # -----------------------------------------
        # Connect to Gmail SMTP
        # -----------------------------------------

        with smtplib.SMTP(
            "smtp.gmail.com",
            587
        ) as server:

            server.starttls()

            server.login(
                sender_email,
                app_password
            )

            server.send_message(
                message
            )


        return (
            f"Email successfully sent to {recipient}."
        )


    except Exception as e:

        return (
            f"Failed to send email: {str(e)}"
        )

# WhatsApp tool
@tool
def send_whatsapp_message(phone_number: str, message: str) -> str:
    """
    Send a WhatsApp message to a phone number.
    Use this tool when the user explicitly asks to send a WhatsApp message.
    """



    # HITL
    decision = interrupt(f"Do you want to send {message} to {phone_number}? (yes/no)")
    
    if isinstance(decision, str) and decision.lower().strip() != "yes":
    
        return "WhatsApp message sending aborted by the user."
    


    try:
        pywhatkit.sendwhatmsg_instantly(
            phone_number,
            message,
            wait_time=10,
            tab_close=True
        )

        return f"WhatsApp message sent successfully to {phone_number}."

    except Exception as e:
        return f"Failed to send WhatsApp message: {str(e)}"


# Create tools list
tools = [rag_tool, search_tool, get_weather_data, calculator, send_email, send_whatsapp_message]

# Bind tools to llm
llm_with_tools = llm.bind_tools(tools)


# Define state
class GPTState(TypedDict):

    messages: Annotated[list[BaseMessage], add_messages]
    thread_id: str


# Create nodes
# Chat node
def chat_node(state: GPTState):
    messages = state["messages"]

    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}

# Tools node
tools_node = ToolNode(tools)


# DB connection
conn = sqlite3.connect(database="agenticgpt.db", check_same_thread=False)
checkpoint = SqliteSaver(conn)


# Define Graph & Compile
graph = StateGraph(GPTState)

# Add nodes
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tools_node)

# Add edges
graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")

# Compile
agenticgpt = graph.compile(checkpointer=checkpoint)


# Get all threads
def get_all_threads():
    all_threads = set()
    for chk in checkpoint.list(None):
        all_threads.add(chk.config["configurable"]["thread_id"])

    return list(all_threads)






# Run the agent
if __name__ == "__main__":

    thread_id = "thread_001"
    config = {"configurable": {"thread_id": thread_id}}

    while True:
        user_input = input("User: ")
        if user_input.lower().strip() in ["exit", "quit"]:
            print("Goodbye!")
            break
    
        initial_state = {"messages": [HumanMessage(content=user_input)]}

        result = agenticgpt.invoke(initial_state, config=config)

        interrupts = result.get("__interrupt__", [])

        if interrupts:
            prompt_to_human = interrupts[0].value
            print(f"HITL: {prompt_to_human}")
            decision = input("Your decision: ").strip().lower()

            result = agenticgpt.invoke(
                Command(resume=decision),
                config=config
            )

        print("Assistant: ", result["messages"][-1].content[0]["text"])
        print("="*120)