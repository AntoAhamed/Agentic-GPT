# ============================================================
# IMPORTS
# ============================================================
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

import hashlib
import secrets
import uuid
import re
import shutil

# Removed imports for free deployment on Render
# import smtplib
# from email.message import EmailMessage
# import pywhatkit


# ============================================================
# ENVIRONMENT
# ============================================================
load_dotenv()


# Define LLM
model = "gemini-3.1-flash-lite"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
WEATHERAPI_API_KEY = os.environ.get("WEATHERAPI_API_KEY")


# ============================================================
# DATABASE
# ============================================================
conn = sqlite3.connect(database="agenticgpt.db", check_same_thread=False)

conn.execute("PRAGMA foreign_keys = ON")

checkpoint = SqliteSaver(conn)


# ============================================================
# AUTHENTICATION
# ============================================================

# ============================================================
# USER AUTHENTICATION DATABASE
# ============================================================

def init_auth_db():
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS thread_owners (
            thread_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()


init_auth_db()


# ============================================================
# PASSWORD HASHING
# ============================================================

def hash_password(password: str) -> str:

    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        600_000
    )

    return (
        salt.hex()
        + ":"
        + password_hash.hex()
    )


def verify_password(password: str, stored_hash: str) -> bool:

    try:

        salt_hex, hash_hex = stored_hash.split(":")

        salt = bytes.fromhex(salt_hex)

        expected_hash = bytes.fromhex(hash_hex)

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            600_000
        )

        return secrets.compare_digest(
            password_hash,
            expected_hash
        )

    except Exception:

        return False


# ============================================================
# EMAIL VALIDATION
# ============================================================

EMAIL_REGEX = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
)


def is_valid_email(email: str) -> bool:
    """
    Validate basic email syntax.

    This checks that the email:
    - contains a valid local part
    - contains @
    - contains a domain
    - contains at least one domain extension
    """
    if not email:
        return False

    email = email.strip()

    # RFC practical maximum length.
    if len(email) > 254:
        return False

    if not EMAIL_REGEX.fullmatch(email):
        return False

    return True


# ============================================================
# SIGNUP
# ============================================================

def signup(username, email, password):
    username = username.strip()
    email = email.strip().lower()
    password = password or ""

    # --------------------------------------------------------
    # BASIC VALIDATION
    # --------------------------------------------------------

    if not username:
        return False, "Username is required."

    if len(username) < 3:
        return False, "Username must be at least 3 characters."

    if len(username) > 50:
        return False, "Username must be 50 characters or fewer."

    # --------------------------------------------------------
    # EMAIL VALIDATION
    # --------------------------------------------------------

    if not is_valid_email(email):
        return False, "Please enter a valid email address."

    # --------------------------------------------------------
    # PASSWORD VALIDATION
    # --------------------------------------------------------

    if len(password) < 8:
        return False, "Password must be at least 8 characters."

    # --------------------------------------------------------
    # CREATE USER
    # --------------------------------------------------------

    try:
        password_hash = hash_password(password)

        user_id = str(uuid.uuid4())

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO users (
                id,
                username,
                email,
                password_hash
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                email,
                password_hash,
            ),
        )

        # Create persistent session.
        session_token = secrets.token_urlsafe(32)

        cursor.execute(
            """
            INSERT INTO sessions (
                token,
                user_id
            )
            VALUES (?, ?)
            """,
            (
                session_token,
                user_id,
            ),
        )

        conn.commit()

        return True, {
            "id": user_id,
            "username": username,
            "email": email,
            "session_token": session_token,
        }

    except sqlite3.IntegrityError as e:

        conn.rollback()

        error_message = str(e).lower()

        if "email" in error_message:
            return False, "An account with this email already exists."

        if "username" in error_message:
            return False, "That username is already taken."

        return False, "Unable to create account."

    except Exception as e:

        conn.rollback()

        return False, "Unable to create account."


# ============================================================
# LOGIN
# ============================================================

def login(email: str, password: str):

    email = email.strip().lower()

    cursor = conn.execute(
        """
        SELECT
            id,
            username,
            email,
            password_hash
        FROM users
        WHERE email = ?
        """,
        (email,)
    )

    user = cursor.fetchone()

    if not user:

        return False, "Invalid email or password."

    user_id = user[0]
    username = user[1]
    user_email = user[2]
    stored_hash = user[3]

    if not verify_password(
        password,
        stored_hash
    ):

        return False, "Invalid email or password."

    # --------------------------------------------------------
    # Create persistent session token
    # --------------------------------------------------------

    session_token = secrets.token_urlsafe(32)

    conn.execute(
        """
        INSERT INTO sessions (
            token,
            user_id
        )
        VALUES (?, ?)
        """,
        (
            session_token,
            user_id
        )
    )

    conn.commit()

    return True, {
        "id": user_id,
        "username": username,
        "email": user_email,
        "session_token": session_token
    }


def get_user_from_session(session_token: str):

    if not session_token:
        return None

    cursor = conn.execute(
        """
        SELECT
            users.id,
            users.username,
            users.email
        FROM sessions
        JOIN users
            ON sessions.user_id = users.id
        WHERE sessions.token = ?
        """,
        (session_token,)
    )

    user = cursor.fetchone()

    if not user:
        return None

    return {
        "id": user[0],
        "username": user[1],
        "email": user[2]
    }


def delete_session(session_token: str):

    if not session_token:
        return

    conn.execute(
        """
        DELETE FROM sessions
        WHERE token = ?
        """,
        (session_token,)
    )

    conn.commit()


# ============================================================
# THREAD OWNERSHIP
# ============================================================

def create_thread(user_id: str, thread_id: str):

    cursor = conn.execute(
        """
        SELECT 1
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    )

    if cursor.fetchone() is None:
        raise ValueError(
            "User does not exist."
        )

    conn.execute(
        """
        INSERT INTO thread_owners (
            thread_id,
            user_id
        )
        VALUES (?, ?)
        """,
        (
            thread_id,
            user_id
        )
    )

    conn.commit()


def thread_belongs_to_user(
    thread_id: str,
    user_id: str
) -> bool:

    cursor = conn.execute(
        """
        SELECT 1
        FROM thread_owners
        WHERE thread_id = ?
        AND user_id = ?
        """,
        (
            thread_id,
            user_id
        )
    )

    return cursor.fetchone() is not None


# ============================================================
# DELETE CONVERSATION
# ============================================================

def delete_conversation(user_id: str, thread_id: str):
    """
    Permanently delete a conversation belonging to a user.

    Deletes:
        1. LangGraph checkpoints
        2. thread_owners record
        3. uploaded PDFs
        4. FAISS index

    Security:
        The conversation MUST belong to the authenticated user.
    """

    if not user_id:
        raise PermissionError(
            "User authentication is invalid."
        )

    if not thread_id:
        raise ValueError(
            "Thread ID is required."
        )

    # --------------------------------------------------------
    # SECURITY CHECK
    # --------------------------------------------------------

    if not thread_belongs_to_user(
        thread_id,
        user_id,
    ):
        raise PermissionError(
            "You do not have permission to delete this conversation."
        )

    # --------------------------------------------------------
    # DELETE LANGGRAPH CHECKPOINTS
    # --------------------------------------------------------

    try:

        checkpoint.delete_thread(
            thread_id
        )

    except Exception as e:

        raise RuntimeError(
            f"Unable to delete conversation: {str(e)}"
        )

    # --------------------------------------------------------
    # DELETE THREAD OWNERSHIP
    # --------------------------------------------------------

    try:

        cursor = conn.execute(
            """
            DELETE FROM thread_owners
            WHERE thread_id = ?
            AND user_id = ?
            """,
            (
                thread_id,
                user_id,
            )
        )

        conn.commit()

    except Exception as e:

        conn.rollback()

        raise RuntimeError(
            f"Unable to delete conversation ownership: {str(e)}"
        )

    # --------------------------------------------------------
    # DELETE UPLOADED PDF DIRECTORY
    # --------------------------------------------------------

    pdf_directory = os.path.join(
        "uploaded_pdfs",
        thread_id
    )

    if os.path.isdir(pdf_directory):

        try:

            shutil.rmtree(
                pdf_directory
            )

        except Exception:
            pass

    # --------------------------------------------------------
    # DELETE FAISS DIRECTORY
    # --------------------------------------------------------

    faiss_directory = os.path.join(
        "faiss_db",
        thread_id
    )

    if os.path.isdir(faiss_directory):

        try:

            shutil.rmtree(
                faiss_directory
            )

        except Exception:
            pass

    return True


# ============================================================
# LLM
# ============================================================
llm = ChatGoogleGenerativeAI(model = model, api_key = GEMINI_API_KEY)


# ============================================================
# RAG
# ============================================================
embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")

def ingest_rag_documents(file_path, thread_id, user_id):
    """
    Add a PDF to the RAG knowledge base
    belonging only to this conversation.
    """

    if not thread_belongs_to_user(thread_id, user_id):
        raise PermissionError(
            "You do not have access to this conversation."
        )

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


def get_retriever(thread_id, user_id):
    """
    Return a retriever only if the conversation
    belongs to the authenticated user.
    """

    if not thread_belongs_to_user(
        thread_id,
        user_id
    ):
        return None

    base_db_path = "faiss_db"

    db_path = os.path.join(
        base_db_path,
        thread_id
    )

    index_file = os.path.join(
        db_path,
        "index.faiss"
    )

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


# ============================================================
# TOOLS
# ============================================================

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

        user_id = runtime.state.get("user_id")

        if not thread_id or not user_id:

            return (
                "Unable to determine the current conversation."
            )

        if not thread_belongs_to_user(
            thread_id,
            user_id
        ):

            return "You do not have access to this conversation."


        # -----------------------------------------
        # Get conversation-specific retriever
        # -----------------------------------------

        retriever = get_retriever(
            thread_id,
            user_id
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

    response = requests.get(url, timeout=10)

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



# Email and WhatsApp tools are removed to deploy on Render for free
# Email tool
# @tool
# def send_email(
#     recipient: str,
#     subject: str,
#     body: str
# ) -> str:
#     """
#     Send an email to a recipient.

#     Use this tool when the user explicitly asks to send
#     an email.

#     Args:
#         recipient: Email address of the recipient.
#         subject: Subject of the email.
#         body: Complete email body.
#     """



#     # HITL
#     decision = interrupt(f"Do you want to send {body} to {recipient}? (yes/no)")

#     if isinstance(decision, str) and decision.lower().strip() != "yes":

#         return "Email sending aborted by the user."

    

#     sender_email = os.environ.get(
#         "EMAIL_ADDRESS"
#     )

#     app_password = os.environ.get(
#         "EMAIL_APP_PASSWORD"
#     )

#     if not sender_email or not app_password:

#         return (
#             "Email configuration is missing. "
#             "Please configure EMAIL_ADDRESS and "
#             "EMAIL_APP_PASSWORD in the .env file."
#         )


#     try:

#         # -----------------------------------------
#         # Create email
#         # -----------------------------------------

#         message = EmailMessage()

#         message["From"] = sender_email
#         message["To"] = recipient
#         message["Subject"] = subject

#         message.set_content(
#             body
#         )


#         # -----------------------------------------
#         # Connect to Gmail SMTP
#         # -----------------------------------------

#         with smtplib.SMTP(
#             "smtp.gmail.com",
#             587
#         ) as server:

#             server.starttls()

#             server.login(
#                 sender_email,
#                 app_password
#             )

#             server.send_message(
#                 message
#             )


#         return (
#             f"Email successfully sent to {recipient}."
#         )


#     except Exception as e:

#         return (
#             f"Failed to send email: {str(e)}"
#         )

# WhatsApp tool
# @tool
# def send_whatsapp_message(phone_number: str, message: str) -> str:
#     """
#     Send a WhatsApp message to a phone number.
#     Use this tool when the user explicitly asks to send a WhatsApp message.
#     """



#     # HITL
#     decision = interrupt(f"Do you want to send {message} to {phone_number}? (yes/no)")
    
#     if isinstance(decision, str) and decision.lower().strip() != "yes":
    
#         return "WhatsApp message sending aborted by the user."
    


#     try:
#         pywhatkit.sendwhatmsg_instantly(
#             phone_number,
#             message,
#             wait_time=10,
#             tab_close=True
#         )

#         return f"WhatsApp message sent successfully to {phone_number}."

#     except Exception as e:
#         return f"Failed to send WhatsApp message: {str(e)}"


# Create tools list
# tools = [rag_tool, search_tool, get_weather_data, calculator, send_email, send_whatsapp_message]
tools = [rag_tool, search_tool, get_weather_data, calculator] # Removed tools to deploy to free plan on Render

# Bind tools to llm
llm_with_tools = llm.bind_tools(tools)


# ============================================================
# STATE
# ============================================================
class GPTState(TypedDict):

    messages: Annotated[list[BaseMessage], add_messages]
    thread_id: str
    user_id: str


# ============================================================
# GRAPH
# ============================================================

# Chat node
def chat_node(state: GPTState):
    messages = state["messages"]

    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}

# Tools node
tools_node = ToolNode(tools)

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


# ============================================================
# USER THREADS
# ============================================================
def get_all_threads(user_id: str):

    all_threads = set()

    cursor = conn.execute(
        """
        SELECT thread_id
        FROM thread_owners
        WHERE user_id = ?
        """,
        (user_id,)
    )

    owned_threads = {
        row[0]
        for row in cursor.fetchall()
    }

    for chk in checkpoint.list(None):

        thread_id = chk.config["configurable"]["thread_id"]

        if thread_id in owned_threads:

            all_threads.add(thread_id)

    return list(all_threads)
