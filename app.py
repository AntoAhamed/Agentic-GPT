import streamlit as st
import uuid
import os
import re

from streamlit_mic_recorder import speech_to_text

from backend import (
    agenticgpt,
    get_all_threads,
    ingest_rag_documents
)

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AgenticGPT",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* ==============================
       GLOBAL
       ============================== */

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    /* Main application background */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    main,
    section.main {
        background-color: #212121 !important;
    }

    /* Streamlit top header */
    header[data-testid="stHeader"] {
        background-color: #212121 !important;
    }

    /* Remove the header's shadow/border */
    header[data-testid="stHeader"]::after {
        display: none !important;
    }

    /* Bottom area around chat input */
    [data-testid="stBottomBlockContainer"] {
        background-color: #212121 !important;
    }

    [data-testid="stBottomBlockContainer"]::before {
        background: #212121 !important;
    }

    /* Chat input container */
    [data-testid="stChatInput"] {
        background-color: #212121 !important;
    }

    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                    Roboto, Helvetica, Arial, sans-serif;
    }


    /* ==============================
       SIDEBAR
       ============================== */

    section[data-testid="stSidebar"] {
        background-color: #171717;
        border-right: 1px solid #2f2f2f;
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 1rem;
    }

    .sidebar-header {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 8px 18px 8px;
    }

    .logo {
        width: 34px;
        height: 34px;
        border-radius: 10px;
        background: #ffffff;
        color: #171717;

        display: flex;
        align-items: center;
        justify-content: center;

        font-size: 19px;
        font-weight: 700;
    }

    .brand-name {
        color: #f5f5f5;
        font-size: 18px;
        font-weight: 600;
    }

    .history-title {
        color: #8e8e8e;
        font-size: 12px;
        font-weight: 600;
        padding: 8px 10px;

        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    section[data-testid="stSidebar"] .stButton > button {
        width: 100%;
        border-radius: 8px;

        border: 1px solid #3a3a3a;
        background-color: transparent;
        color: #eeeeee;

        text-align: left;

        padding: 10px 12px;
        margin-bottom: 7px;

        transition: background-color 0.15s ease;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #2a2a2a;
        border-color: #444444;
    }


    /* ==============================
       TOP BAR
       ============================== */

    .top-bar {
        height: 50px;

        display: flex;
        align-items: center;
        justify-content: center;

        color: #eeeeee;
        font-size: 14px;
        font-weight: 500;

        border-bottom: 1px solid #2d2d2d;

        margin-bottom: 10px;
    }


    /* ==============================
       WELCOME SCREEN
       ============================== */

    .main-title {
        text-align: center;

        color: #f5f5f5;

        font-size: 30px;
        font-weight: 600;

        margin-top: 15vh;
        margin-bottom: 10px;
    }

    .main-subtitle {
        text-align: center;

        color: #9b9b9b;

        font-size: 15px;

        margin-bottom: 30px;
    }


    /* ==============================
       SUGGESTION CARDS
       ============================== */

    .suggestion-card {
        background-color: #2a2a2a;

        border: 1px solid #3a3a3a;

        border-radius: 12px;

        padding: 16px;

        height: 100%;
    }

    .suggestion-title {
        color: #eeeeee;

        font-size: 14px;
        font-weight: 600;

        margin-bottom: 6px;
    }

    .suggestion-text {
        color: #9b9b9b;

        font-size: 13px;
    }


    /* ========================================================
       CHAT MESSAGE LAYOUT
       ======================================================== */

    [data-testid="stChatMessage"] {
        background-color: transparent !important;
        padding: 0 !important;
        margin-top: 18px;
        margin-bottom: 18px;
    }


    /* ==============================
       ASSISTANT MESSAGE — LEFT
       ============================== */

    [data-testid="stChatMessage"]:has(
        [data-testid="chatAvatarIcon-assistant"]
    ) {
        justify-content: flex-start;
    }

    [data-testid="stChatMessage"]:has(
        [data-testid="chatAvatarIcon-assistant"]
    ) > div:last-child {
        max-width: 75%;
        color: #eeeeee;
    }


    /* ==============================
       USER MESSAGE — RIGHT
       ============================== */

    [data-testid="stChatMessage"]:has(
        [data-testid="chatAvatarIcon-user"]
    ) {
        justify-content: flex-end;
    }

    [data-testid="stChatMessage"]:has(
        [data-testid="chatAvatarIcon-user"]
    ) > div:last-child {
        max-width: 70%;

        background-color: #2f2f2f;

        border-radius: 18px;

        padding: 10px 16px;

        color: #ffffff;
    }


    /* ==============================
       CHAT MESSAGE TEXT
       ============================== */

    [data-testid="stChatMessage"] p {
        font-size: 15px;
        line-height: 1.65;
    }

    [data-testid="stChatMessage"] pre {
        border-radius: 8px;
    }


    /* ==============================
       CHAT INPUT
       ============================== */

    [data-testid="stChatInput"] {
        bottom: 20px;
    }

    [data-testid="stChatInput"] textarea {
        background-color: #2f2f2f;

        color: #ffffff;

        border: 1px solid #454545;

        border-radius: 14px;

        padding: 12px 14px;
    }

    [data-testid="stChatInput"] textarea:focus {
        border-color: #666666;

        box-shadow: none;
    }


    /* ==============================
       FOOTER
       ============================== */

    .footer-text {
        text-align: center;

        color: #666666;

        font-size: 11px;

        margin-top: 12px;
        margin-bottom: 5px;
    }


    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = {}

if "initialized" not in st.session_state:
    st.session_state.initialized = False

# ============================================================
# HITL SESSION STATE
# ============================================================

if "pending_interrupt" not in st.session_state:
    st.session_state.pending_interrupt = None

if "pending_interrupt_thread" not in st.session_state:
    st.session_state.pending_interrupt_thread = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def extract_text(content):
    """
    Convert LangChain/Gemini message content
    into plain text.
    """

    if isinstance(content, str):
        return content

    if isinstance(content, list):

        text_parts = []

        for item in content:

            if isinstance(item, str):
                text_parts.append(item)

            elif isinstance(item, dict):

                if item.get("type") == "text":
                    text_parts.append(
                        item.get("text", "")
                    )

                elif "text" in item:
                    text_parts.append(
                        item["text"]
                    )

        return "".join(text_parts)

    return str(content)


def extract_pdf_display_info(content):
    """
    Detect the internal PDF instruction message
    and extract only the information that should
    be displayed to the user.

    Returns:
        (filename, user_request)

    or:
        (None, None)
    """

    text = extract_text(content)

    if not text:
        return None, None

    # Check whether this is our internal PDF message
    if "The user has uploaded a PDF named" not in text:
        return None, None

    # Extract filename
    filename_match = re.search(
        r'The user has uploaded a PDF named "(.*?)"',
        text,
        re.DOTALL
    )

    # Extract user's actual request
    request_match = re.search(
        r"The user's request is:\s*(.*?)\s*IMPORTANT:",
        text,
        re.DOTALL
    )

    filename = (
        filename_match.group(1).strip()
        if filename_match
        else None
    )

    user_request = (
        request_match.group(1).strip()
        if request_match
        else ""
    )

    return filename, user_request


def get_display_info(message):
    """
    Convert a persisted LangGraph message into
    what should actually be displayed in the UI.
    """

    if isinstance(message, HumanMessage):

        filename, user_request = extract_pdf_display_info(
            message.content
        )

        # PDF message
        if filename:

            return {
                "type": "pdf",
                "filename": filename,
                "text": user_request
            }

        # Normal user message
        return {
            "type": "text",
            "text": extract_text(message.content)
        }

    elif isinstance(message, AIMessage):

        return {
            "type": "text",
            "text": extract_text(message.content)
        }

    return {
        "type": "text",
        "text": ""
    }


def generate_title(messages):
    """
    Generate a readable conversation title
    using the first real user request.
    """

    for message in messages:

        if isinstance(message, HumanMessage):

            display_info = get_display_info(message)

            text = display_info.get("text", "").strip()

            if not text:
                continue

            if len(text) > 32:
                return text[:32] + "..."

            return text

    return "New Chat"


def load_thread(thread_id):
    """
    Load messages from LangGraph
    SQLite persistence.
    """

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    try:

        state = agenticgpt.get_state(config)

        if not state or not state.values:
            return []

        return state.values.get(
            "messages",
            []
        )

    except Exception:
        return []


def create_new_chat():
    """
    Create a completely new conversation.
    """

    st.session_state.thread_id = str(
        uuid.uuid4()
    )

    st.session_state.messages = []

    # Clear any pending HITL request
    st.session_state.pending_interrupt = None
    st.session_state.pending_interrupt_thread = None

    st.rerun()


def switch_thread(thread_id):
    """
    Switch to an existing conversation.
    """

    messages = load_thread(thread_id)

    st.session_state.thread_id = thread_id

    st.session_state.messages = messages

    # Clear any HITL request from previous conversation
    st.session_state.pending_interrupt = None
    st.session_state.pending_interrupt_thread = None

    st.rerun()


def refresh_threads():
    """
    Get all persisted threads and create
    readable conversation titles.
    """

    threads = get_all_threads()

    chat_threads = {}

    for thread_id in threads:

        messages = load_thread(thread_id)

        title = generate_title(messages)

        chat_threads[thread_id] = title

    st.session_state.chat_threads = chat_threads


# ============================================================
# HITL HELPER
# ============================================================

def get_pending_interrupt(thread_id):
    """
    Check whether the current LangGraph thread
    is paused at an interrupt.
    """

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    try:

        state = agenticgpt.get_state(config)

        if not state or not state.tasks:
            return None

        for task in state.tasks:

            interrupts = getattr(
                task,
                "interrupts",
                None
            )

            if interrupts:

                return interrupts[0].value

    except Exception:
        return None

    return None


# ============================================================
# INITIALIZE
# ============================================================

if not st.session_state.initialized:

    refresh_threads()

    st.session_state.initialized = True


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    # -----------------------------------------
    # Logo / Brand
    # -----------------------------------------

    st.html(
        """
        <div class="sidebar-header">

            <div class="logo">
                ✦
            </div>

            <div class="brand-name">
                AgenticGPT
            </div>

        </div>
        """
    )


    # -----------------------------------------
    # New Chat
    # -----------------------------------------

    if st.button(
        "＋  New chat",
        key="new_chat",
        use_container_width=True
    ):
        create_new_chat()


    # -----------------------------------------
    # History heading
    # -----------------------------------------

    st.html(
        """
        <div class="history-title">
            Your chats
        </div>
        """
    )


    # -----------------------------------------
    # Refresh conversations
    # -----------------------------------------

    refresh_threads()

    thread_items = list(
        st.session_state.chat_threads.items()
    )


    # -----------------------------------------
    # Conversation list
    # -----------------------------------------

    if thread_items:

        for thread_id, title in thread_items:

            is_current = (
                thread_id
                == st.session_state.thread_id
            )

            if is_current:
                button_label = f"●  {title}"
            else:
                button_label = f"   {title}"


            if st.button(
                button_label,
                key=f"thread_{thread_id}",
                use_container_width=True
            ):

                switch_thread(thread_id)

    else:

        st.caption(
            "No previous conversations"
        )


    # -----------------------------------------
    # Sidebar footer
    # -----------------------------------------

    st.markdown("---")

    st.caption(
        "Powered by Gemini + LangGraph"
    )


# ============================================================
# TOP BAR
# ============================================================

st.html(
    """
    <div class="top-bar">
        AgenticGPT
    </div>
    """
)


# ============================================================
# WELCOME SCREEN
# ============================================================

if not st.session_state.messages:

    st.html(
        """
        <div class="main-title">
            How can I help you today?
        </div>
        """
    )

    st.html(
        """
        <div class="main-subtitle">
            Ask questions, search the web,
            calculate, check the weather,
            or ask questions about your PDF.
        </div>
        """
    )


    col1, col2, col3 = st.columns(3)


    with col1:

        st.html(
            """
            <div class="suggestion-card">

                <div class="suggestion-title">
                    🔎 Search the web
                </div>

                <div class="suggestion-text">
                    Find current information
                    from the web.
                </div>

            </div>
            """
        )


    with col2:

        st.html(
            """
            <div class="suggestion-card">

                <div class="suggestion-title">
                    📄 Ask your PDF
                </div>

                <div class="suggestion-text">
                    Upload a PDF and ask
                    questions about its content.
                </div>

            </div>
            """
        )


    with col3:

        st.html(
            """
            <div class="suggestion-card">

                <div class="suggestion-title">
                    🧮 Calculate
                </div>

                <div class="suggestion-text">
                    Perform mathematical
                    calculations accurately.
                </div>

            </div>
            """
        )


# ============================================================
# DISPLAY EXISTING MESSAGES
# ============================================================

for message in st.session_state.messages:

    # ========================================================
    # USER MESSAGE
    # ========================================================

    if isinstance(message, HumanMessage):

        display_info = get_display_info(message)

        message_type = display_info["type"]

        text = display_info["text"]

        filename = display_info.get("filename")


        with st.chat_message("user"):

            # -----------------------------------------------
            # PDF attachment
            # -----------------------------------------------

            if message_type == "pdf":

                st.caption(
                    f"📄 {filename}"
                )

            # -----------------------------------------------
            # User's actual text
            # -----------------------------------------------

            if text:

                st.markdown(text)


    # ========================================================
    # AI MESSAGE
    # ========================================================

    elif isinstance(message, AIMessage):

        content = extract_text(
            message.content
        )

        if content:

            with st.chat_message("assistant"):

                st.markdown(content)


# ============================================================
# HITL APPROVAL UI
# ============================================================

if (
    st.session_state.pending_interrupt is not None
    and
    st.session_state.pending_interrupt_thread
    == st.session_state.thread_id
):

    interrupt_value = (
        st.session_state.pending_interrupt
    )

    # --------------------------------------------------------
    # Support dictionary interrupt payloads
    # --------------------------------------------------------

    if isinstance(interrupt_value, dict):

        interrupt_message = interrupt_value.get(
            "message",
            "Do you want to continue?"
        )

        recipient = interrupt_value.get(
            "recipient"
        )

        subject = interrupt_value.get(
            "subject"
        )

        body = interrupt_value.get(
            "body"
        )

    # --------------------------------------------------------
    # Your current backend uses a string interrupt
    # --------------------------------------------------------

    else:

        interrupt_message = str(
            interrupt_value
        )

        recipient = None
        subject = None
        body = None


    # --------------------------------------------------------
    # Display HITL message
    # --------------------------------------------------------

    st.warning(
        f"⚠️ **Approval Required**\n\n"
        f"{interrupt_message}"
    )


    # --------------------------------------------------------
    # Display email details if available
    # --------------------------------------------------------

    if recipient:

        st.markdown(
            f"**Recipient:** {recipient}"
        )

        st.markdown(
            f"**Subject:** {subject}"
        )

        st.markdown(
            f"**Message:**\n\n{body}"
        )


    # --------------------------------------------------------
    # HITL buttons
    # --------------------------------------------------------

    col1, col2 = st.columns(2)


    with col1:

        approve = st.button(
            "✅ Send Email",
            key="hitl_approve",
            use_container_width=True
        )


    with col2:

        reject = st.button(
            "❌ Cancel",
            key="hitl_reject",
            use_container_width=True
        )


    # ========================================================
    # APPROVE EMAIL
    # ========================================================

    if approve:

        config = {
            "configurable": {
                "thread_id":
                    st.session_state.thread_id
            }
        }

        # Clear pending interrupt before resuming
        st.session_state.pending_interrupt = None

        st.session_state.pending_interrupt_thread = None


        with st.chat_message("assistant"):

            with st.spinner("Thinking..."):

                assistant_placeholder = st.empty()

                full_response = ""


                try:

                    # -----------------------------------------
                    # Resume interrupted graph
                    # -----------------------------------------

                    for message_chunk, metadata in agenticgpt.stream(

                        Command(
                            resume="yes"
                        ),

                        config=config,

                        stream_mode="messages"
                    ):

                        if not isinstance(
                            message_chunk,
                            AIMessage
                        ):
                            continue


                        content = extract_text(
                            message_chunk.content
                        )


                        if not content:
                            continue


                        full_response += content


                        assistant_placeholder.markdown(
                            full_response + "▌"
                        )


                    # -----------------------------------------
                    # Final response
                    # -----------------------------------------

                    assistant_placeholder.markdown(
                        full_response
                    )


                except Exception as e:

                    full_response = (
                        "Sorry, something went wrong.\n\n"
                        f"`{str(e)}`"
                    )

                    assistant_placeholder.markdown(
                        full_response
                    )


        # ----------------------------------------------------
        # Save assistant response
        # ----------------------------------------------------

        if full_response:

            st.session_state.messages.append(
                AIMessage(
                    content=full_response
                )
            )


        refresh_threads()

        st.rerun()


    # ========================================================
    # REJECT EMAIL
    # ========================================================

    if reject:

        config = {
            "configurable": {
                "thread_id":
                    st.session_state.thread_id
            }
        }

        # Clear pending interrupt before resuming
        st.session_state.pending_interrupt = None

        st.session_state.pending_interrupt_thread = None


        with st.chat_message("assistant"):

            with st.spinner("Thinking..."):

                assistant_placeholder = st.empty()

                full_response = ""


                try:

                    # -----------------------------------------
                    # Resume interrupted graph
                    # -----------------------------------------

                    for message_chunk, metadata in agenticgpt.stream(

                        Command(
                            resume="no"
                        ),

                        config=config,

                        stream_mode="messages"
                    ):

                        if not isinstance(
                            message_chunk,
                            AIMessage
                        ):
                            continue


                        content = extract_text(
                            message_chunk.content
                        )


                        if not content:
                            continue


                        full_response += content


                        assistant_placeholder.markdown(
                            full_response + "▌"
                        )


                    # -----------------------------------------
                    # Final response
                    # -----------------------------------------

                    assistant_placeholder.markdown(
                        full_response
                    )


                except Exception as e:

                    full_response = (
                        "Sorry, something went wrong.\n\n"
                        f"`{str(e)}`"
                    )

                    assistant_placeholder.markdown(
                        full_response
                    )


        # ----------------------------------------------------
        # Save assistant response
        # ----------------------------------------------------

        if full_response:

            st.session_state.messages.append(
                AIMessage(
                    content=full_response
                )
            )


        refresh_threads()

        st.rerun()


# ============================================================
# CHAT INPUT
# ============================================================

chat_input = st.chat_input(
    "Message AgenticGPT...",
    accept_file=True,
    file_type=["pdf"]
)


# ============================================================
# EXTRACT CHAT INPUT
# ============================================================

user_input = None
uploaded_file = None

if chat_input:

    if isinstance(chat_input, str):

        user_input = chat_input

    else:

        user_input = chat_input.text

        if chat_input.files:

            uploaded_file = chat_input.files[0]


# ============================================================
# PROCESS USER INPUT
# ============================================================

if chat_input:

    # ========================================================
    # HANDLE PDF UPLOAD
    # ========================================================

    if uploaded_file:

        upload_dir = os.path.join(
            "uploaded_pdfs",
            st.session_state.thread_id
        )

        os.makedirs(
            upload_dir,
            exist_ok=True
        )

        file_path = os.path.join(
            upload_dir,
            uploaded_file.name
        )

        try:

            # -----------------------------------------
            # Save PDF
            # -----------------------------------------

            with open(
                file_path,
                "wb"
            ) as f:

                f.write(
                    uploaded_file.getbuffer()
                )


            # -----------------------------------------
            # Index PDF
            # -----------------------------------------

            with st.spinner(
                "Reading and indexing PDF..."
            ):

                ingest_rag_documents(
                    file_path,
                    st.session_state.thread_id
                )


        except Exception as e:

            st.error(
                f"Failed to process PDF: {str(e)}"
            )

            st.stop()


    # ========================================================
    # USER MESSAGE
    # ========================================================

    if user_input or uploaded_file:

        # ====================================================
        # MESSAGE SENT TO LANGGRAPH
        # ====================================================

        if uploaded_file:

            user_message_content = f"""
            The user has uploaded a PDF named "{uploaded_file.name}".

            The user's request is:

            {user_input}

            IMPORTANT:
            The uploaded PDF has already been indexed in the RAG system.

            The uploaded PDF is now available as context for the user's request.

            If the user's request requires information from the PDF,
            you MUST call the rag_tool and use the retrieved information
            to answer the user's request.

            Follow the user's request exactly. Do not automatically
            summarize the PDF unless the user explicitly asks for a summary.

            Do NOT ask the user to upload or provide the document again.
            """

        else:

            user_message_content = user_input


        user_message = HumanMessage(
            content=user_message_content
        )


        # ====================================================
        # CLEAN MESSAGE FOR UI
        # ====================================================

        # IMPORTANT:
        # We store the same internal message in session state,
        # but get_display_info() will hide the internal
        # instructions when rendering it.

        st.session_state.messages.append(
            user_message
        )


        # ====================================================
        # DISPLAY USER MESSAGE
        # ====================================================

        with st.chat_message("user"):

            if uploaded_file:

                st.caption(
                    f"📄 {uploaded_file.name}"
                )

            if user_input:

                st.markdown(
                    user_input
                )


        # ====================================================
        # ASSISTANT RESPONSE
        # ====================================================

        with st.chat_message("assistant"):

            # -----------------------------------------
            # Thinking loader
            # -----------------------------------------

            with st.spinner("Thinking..."):

                assistant_placeholder = st.empty()

                full_response = ""


                # -----------------------------------------
                # LangGraph configuration
                # -----------------------------------------

                config = {
                    "configurable": {
                        "thread_id":
                            st.session_state.thread_id
                    }
                }


                try:

                    # -------------------------------------
                    # Stream response
                    # -------------------------------------

                    for message_chunk, metadata in agenticgpt.stream(

                        {
                            "messages": [
                                user_message
                            ],
                            "thread_id": st.session_state.thread_id
                        },

                        config=config,

                        stream_mode="messages"
                    ):

                        # ---------------------------------
                        # Only process AI messages
                        # ---------------------------------

                        if not isinstance(
                            message_chunk,
                            AIMessage
                        ):
                            continue


                        # ---------------------------------
                        # Extract text
                        # ---------------------------------

                        content = extract_text(
                            message_chunk.content
                        )


                        # ---------------------------------
                        # Ignore empty chunks
                        # ---------------------------------

                        if not content:
                            continue


                        # ---------------------------------
                        # Append chunk
                        # ---------------------------------

                        full_response += content


                        # ---------------------------------
                        # Render Markdown while streaming
                        # ---------------------------------

                        assistant_placeholder.markdown(
                            full_response + "▌"
                        )


                    # =================================================
                    # HITL CHECK
                    # =================================================

                    interrupt_value = get_pending_interrupt(
                        st.session_state.thread_id
                    )


                    if interrupt_value is not None:

                        # ---------------------------------------------
                        # Store interrupt in session state
                        # ---------------------------------------------

                        st.session_state.pending_interrupt = (
                            interrupt_value
                        )

                        st.session_state.pending_interrupt_thread = (
                            st.session_state.thread_id
                        )


                        # ---------------------------------------------
                        # There is no final assistant response yet.
                        # LangGraph is paused.
                        # ---------------------------------------------

                        assistant_placeholder.empty()

                        st.rerun()


                    # -----------------------------------------
                    # Final AI response
                    # -----------------------------------------

                    assistant_placeholder.markdown(
                        full_response
                    )


                except Exception as e:

                    full_response = (
                        "Sorry, something went wrong.\n\n"
                        f"`{str(e)}`"
                    )

                    assistant_placeholder.markdown(
                        full_response
                    )


        # ====================================================
        # SAVE ASSISTANT RESPONSE
        # ====================================================

        if full_response:

            assistant_message = AIMessage(
                content=full_response
            )

            st.session_state.messages.append(
                assistant_message
            )


        # ====================================================
        # REFRESH SIDEBAR
        # ====================================================

        refresh_threads()


        # ====================================================
        # RERUN
        # ====================================================

        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.html(
    """
    <div class="footer-text">
        AgenticGPT can make mistakes.
        Check important information.
    </div>
    """
)