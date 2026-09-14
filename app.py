import streamlit as st
import uuid
import os
import re
import html

from backend_with_auth import (
    agenticgpt,
    get_all_threads,
    ingest_rag_documents,
    signup,
    login,
    create_thread,
    thread_belongs_to_user,
    get_user_from_session,
    delete_session,
    delete_conversation,
)

from langchain_core.messages import HumanMessage, AIMessage

# ============================================================
# IMPORTANT
# ============================================================
# Install:
#
# pip uninstall streamlit-cookies-controller -y
# pip install streamlit-cookies-manager-v2
#
# Render:
# Add environment variable:
#
# COOKIE_PASSWORD=<strong-long-random-secret>
#
# Keep COOKIE_PASSWORD unchanged after deployment.
# ============================================================

from streamlit_cookies_manager import EncryptedCookieManager


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AgenticGPT",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# COOKIE MANAGER
# ============================================================

# IMPORTANT:
# The password must remain the same across application restarts.
#
# For production, set COOKIE_PASSWORD in Render/environment variables.
#
# The fallback is only for local development.
COOKIE_PASSWORD = os.environ.get(
    "COOKIE_PASSWORD",
    "agenticgpt-local-development-cookie-secret-change-this",
)

cookies = EncryptedCookieManager(
    prefix="agenticgpt/",
    password=COOKIE_PASSWORD,
)

# ------------------------------------------------------------
# IMPORTANT:
# Wait until the browser cookie component has loaded.
#
# Without this, on a browser refresh cookies.get(...)
# can temporarily return None and the user can incorrectly
# appear to be logged out.
# ------------------------------------------------------------

if not cookies.ready():
    st.stop()


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* ========================================================
       GLOBAL
       ======================================================== */

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    main,
    section.main {
        background-color: #212121 !important;
    }

    header[data-testid="stHeader"] {
        background-color: #212121 !important;
    }

    header[data-testid="stHeader"]::after {
        display: none !important;
    }

    [data-testid="stBottomBlockContainer"] {
        background-color: #212121 !important;
    }

    [data-testid="stBottomBlockContainer"]::before {
        background: #212121 !important;
    }

    [data-testid="stChatInput"] {
        background-color: #212121 !important;
    }

    html,
    body,
    [class*="css"] {
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Helvetica,
            Arial,
            sans-serif;
    }


    /* ========================================================
       SIDEBAR
       ======================================================== */

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

    .user-info {
        padding: 8px 10px 14px 10px;
        margin-bottom: 8px;

        border-bottom: 1px solid #2f2f2f;
    }

    .user-name {
        color: #f5f5f5;
        font-size: 14px;
        font-weight: 600;
    }

    .user-email {
        color: #777777;
        font-size: 11px;
        margin-top: 3px;

        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
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

        transition:
            background-color 0.15s ease,
            border-color 0.15s ease;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #2a2a2a;
        border-color: #444444;
    }

    .logout-button button {
        color: #ff7b72 !important;
    }

    /* ========================================================
       SIDEBAR CONVERSATION DELETE
       ======================================================== */

    .delete-thread-button button {
        width: 100% !important;
        min-height: 38px !important;
        padding: 0 !important;
        margin: 0 0 7px 0 !important;
        border-radius: 8px !important;
        border: 1px solid #3a3a3a !important;
        background: transparent !important;
        color: #8e8e8e !important;
        text-align: center !important;
    }

    .delete-thread-button button:hover {
        background: #3a2020 !important;
        border-color: #6b3838 !important;
        color: #ff7b72 !important;
    }

    .delete-confirmation {
        background: #242424;
        border: 1px solid #3a3a3a;
        border-radius: 10px;
        padding: 10px;
        margin: -2px 0 9px 0;
    }

    .delete-confirmation-text {
        color: #d0d0d0;
        font-size: 12px;
        line-height: 1.4;
        margin-bottom: 8px;
    }


    /* ========================================================
       TOP BAR
       ======================================================== */

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


    /* ========================================================
       WELCOME SCREEN
       ======================================================== */

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


    /* ========================================================
       SUGGESTION CARDS
       ======================================================== */

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


    /* ========================================================
       ASSISTANT MESSAGE — LEFT
       ======================================================== */

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


    /* ========================================================
       USER MESSAGE — RIGHT
       ======================================================== */

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


    /* ========================================================
       CHAT MESSAGE TEXT
       ======================================================== */

    [data-testid="stChatMessage"] p {
        font-size: 15px;
        line-height: 1.65;
    }

    [data-testid="stChatMessage"] pre {
        border-radius: 8px;
    }


    /* ========================================================
       CHAT INPUT
       ======================================================== */

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


    /* ========================================================
       AUTHENTICATION
       ======================================================== */

    .auth-logo {
        width: 56px;
        height: 56px;

        margin: 0 auto 18px auto;

        border-radius: 16px;

        background: #ffffff;
        color: #171717;

        display: flex;
        align-items: center;
        justify-content: center;

        font-size: 30px;
        font-weight: 700;
    }

    .auth-title {
        text-align: center;

        color: #f5f5f5;

        font-size: 28px;
        font-weight: 600;

        margin-bottom: 7px;
    }

    .auth-subtitle {
        text-align: center;

        color: #8e8e8e;

        font-size: 14px;

        margin-bottom: 0;
    }

    div[data-testid="stForm"] {
        border: 1px solid #303030 !important;

        background-color: #171717 !important;

        border-radius: 16px !important;

        padding: 24px !important;
    }

    div[data-testid="stForm"] label {
        color: #b5b5b5 !important;
    }

    div[data-testid="stForm"] input {
        background-color: #242424 !important;

        color: #ffffff !important;

        border: 1px solid #3d3d3d !important;

        border-radius: 10px !important;
    }

    div[data-testid="stForm"] input:focus {
        border-color: #666666 !important;

        box-shadow: none !important;
    }

    div[data-testid="stForm"] button {
        background-color: #ffffff !important;

        color: #171717 !important;

        border: none !important;

        border-radius: 10px !important;

        font-weight: 600 !important;

        min-height: 42px !important;
    }

    div[data-testid="stForm"] button:hover {
        background-color: #e8e8e8 !important;

        color: #171717 !important;
    }

    .auth-footer {
        text-align: center;

        color: #666666;

        font-size: 11px;

        margin-top: 20px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;

        justify-content: center;

        margin-bottom: 18px;
    }

    .stTabs [data-baseweb="tab"] {
        color: #8e8e8e;

        font-size: 14px;

        padding-left: 18px;
        padding-right: 18px;
    }

    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #ffffff !important;
    }


    /* ========================================================
       FOOTER
       ======================================================== */

    .footer-text {
        text-align: center;

        color: #666666;

        font-size: 11px;

        margin-top: 12px;
        margin-bottom: 5px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "username" not in st.session_state:
    st.session_state.username = None

if "email" not in st.session_state:
    st.session_state.email = None

if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = {}

if "initialized" not in st.session_state:
    st.session_state.initialized = False

if "new_chat_mode" not in st.session_state:
    st.session_state.new_chat_mode = False

if "delete_confirm_thread" not in st.session_state:
    st.session_state.delete_confirm_thread = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def extract_text(content):
    """
    Convert LangChain/Gemini message content into plain text.
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
    and extract only what should be displayed.
    """

    text = extract_text(content)

    if not text:
        return None, None

    if "The user has uploaded a PDF named" not in text:
        return None, None

    filename_match = re.search(
        r'The user has uploaded a PDF named "(.*?)"',
        text,
        re.DOTALL,
    )

    request_match = re.search(
        r"The user's request is:\s*(.*?)\s*IMPORTANT:",
        text,
        re.DOTALL,
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
    Convert persisted LangGraph messages into
    content suitable for displaying in the UI.
    """

    if isinstance(message, HumanMessage):

        filename, user_request = extract_pdf_display_info(
            message.content
        )

        if filename:

            return {
                "type": "pdf",
                "filename": filename,
                "text": user_request,
            }

        return {
            "type": "text",
            "text": extract_text(message.content),
        }

    elif isinstance(message, AIMessage):

        return {
            "type": "text",
            "text": extract_text(message.content),
        }

    return {
        "type": "text",
        "text": "",
    }


def generate_title(messages):
    """
    Generate a readable conversation title
    from the first real user request.
    """

    for message in messages:

        if isinstance(message, HumanMessage):

            display_info = get_display_info(
                message
            )

            text = display_info.get(
                "text",
                "",
            ).strip()

            if not text:
                continue

            if len(text) > 32:
                return text[:32] + "..."

            return text

    return "New Chat"


# ============================================================
# AUTHENTICATION FUNCTIONS
# ============================================================

def set_authenticated_user(user, session_token=None):
    """
    Store authenticated user information in Streamlit
    session state.

    The actual authentication token is stored in the
    encrypted browser cookie.
    """

    st.session_state.authenticated = True

    st.session_state.user_id = user["id"]

    st.session_state.username = user["username"]

    st.session_state.email = user["email"]

    st.session_state.thread_id = None

    st.session_state.messages = []

    st.session_state.chat_threads = {}

    st.session_state.initialized = False

    st.session_state.new_chat_mode = False

    # --------------------------------------------------------
    # Store authentication token in encrypted cookie
    # --------------------------------------------------------

    if session_token:

        try:

            cookies["session_token"] = session_token

            # Force immediate browser persistence.
            cookies.save()

        except Exception as e:

            raise RuntimeError(
                f"Unable to save authentication cookie: {str(e)}"
            )


def restore_authentication():
    """
    Restore authentication after:

    - Browser refresh
    - New Streamlit session
    - Page reload

    The browser stores the encrypted session token.
    The backend validates that token against the SQLite
    sessions table.
    """

    # Already authenticated in this Streamlit session.
    if st.session_state.authenticated:
        return

    # --------------------------------------------------------
    # Read persistent browser cookie
    # --------------------------------------------------------

    try:

        session_token = cookies.get(
            "session_token"
        )

    except Exception:

        session_token = None

    if not session_token:
        return

    # --------------------------------------------------------
    # Validate session token against backend
    # --------------------------------------------------------

    try:

        user = get_user_from_session(
            session_token
        )

    except Exception:

        user = None

    # --------------------------------------------------------
    # Valid session
    # --------------------------------------------------------

    if user:

        # Do NOT save the cookie again here.
        # It already exists in the browser.

        set_authenticated_user(
            user
        )

        return

    # --------------------------------------------------------
    # Invalid / expired / deleted session
    # --------------------------------------------------------

    try:

        del cookies["session_token"]

        cookies.save()

    except Exception:

        pass


def logout():
    """
    Completely log out the current user.

    Removes:

    1. Server-side session record.
    2. Browser authentication cookie.
    3. Streamlit session state.
    """

    # --------------------------------------------------------
    # Get current browser session token
    # --------------------------------------------------------

    try:

        session_token = cookies.get(
            "session_token"
        )

    except Exception:

        session_token = None

    # --------------------------------------------------------
    # Delete server-side session
    # --------------------------------------------------------

    if session_token:

        try:

            delete_session(
                session_token
            )

        except Exception:

            pass

    # --------------------------------------------------------
    # Delete browser cookie
    # --------------------------------------------------------

    try:

        if "session_token" in cookies:

            del cookies["session_token"]

            cookies.save()

    except Exception:

        pass

    # --------------------------------------------------------
    # Clear Streamlit session
    # --------------------------------------------------------

    st.session_state.clear()

    st.rerun()


# ============================================================
# RESTORE AUTHENTICATION
# ============================================================

restore_authentication()


# ============================================================
# THREAD FUNCTIONS
# ============================================================

def create_thread_when_needed():
    """
    Create the thread only when the user actually
    starts sending a message/uploading a PDF.

    Returns the newly-created thread ID.
    """

    if st.session_state.thread_id:
        return st.session_state.thread_id

    user_id = st.session_state.user_id

    if not user_id:
        raise PermissionError(
            "User authentication is invalid."
        )

    new_thread_id = str(
        uuid.uuid4()
    )

    create_thread(
        user_id,
        new_thread_id,
    )

    st.session_state.thread_id = (
        new_thread_id
    )

    st.session_state.chat_threads[
        new_thread_id
    ] = "New Chat"

    st.session_state.new_chat_mode = False

    return new_thread_id


def load_thread(thread_id):
    """
    Load a conversation only if it belongs
    to the authenticated user.
    """

    user_id = st.session_state.user_id

    if not user_id or not thread_id:
        return []

    try:

        if not thread_belongs_to_user(
            thread_id,
            user_id,
        ):

            return []

    except Exception:

        return []

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    try:

        state = agenticgpt.get_state(
            config
        )

        if not state or not state.values:
            return []

        return state.values.get(
            "messages",
            [],
        )

    except Exception:

        return []


def create_new_chat():
    """
    Start a new EMPTY chat in the UI.

    The database thread will only be created
    when the user actually sends a message
    or uploads a PDF.
    """

    st.session_state.thread_id = None

    st.session_state.messages = []

    st.session_state.new_chat_mode = True

    st.rerun()


def switch_thread(thread_id):
    """
    Switch to an existing conversation
    after verifying ownership.
    """

    user_id = st.session_state.user_id

    if not user_id:
        return

    try:

        if not thread_belongs_to_user(
            thread_id,
            user_id,
        ):

            st.error(
                "You do not have access to this conversation."
            )

            return

    except Exception:

        st.error(
            "Unable to verify conversation access."
        )

        return

    messages = load_thread(
        thread_id
    )

    st.session_state.thread_id = (
        thread_id
    )

    st.session_state.messages = messages

    st.session_state.new_chat_mode = False

    st.rerun()


def delete_thread_from_ui(thread_id):
    """Permanently delete a conversation for the authenticated user."""

    user_id = st.session_state.user_id

    if not user_id:
        st.error("Authentication is invalid.")
        return

    if not thread_id:
        return

    try:
        deleted = delete_conversation(user_id, thread_id)

        if not deleted:
            st.error("Conversation could not be deleted.")
            return

    except PermissionError as e:
        st.error(str(e))
        return
    except Exception as e:
        st.error(f"Unable to delete conversation: {str(e)}")
        return

    st.session_state.chat_threads.pop(thread_id, None)

    if st.session_state.thread_id == thread_id:
        st.session_state.thread_id = None
        st.session_state.messages = []
        st.session_state.new_chat_mode = True

    st.session_state.delete_confirm_thread = None
    st.rerun()


def refresh_threads():
    """
    Get conversations belonging only to
    the authenticated user.
    """

    user_id = st.session_state.user_id

    if not user_id:

        st.session_state.chat_threads = {}

        return

    try:

        threads = get_all_threads(
            user_id
        )

    except Exception:

        st.session_state.chat_threads = {}

        return

    chat_threads = {}

    for thread_id in threads:

        messages = load_thread(
            thread_id
        )

        title = generate_title(
            messages
        )

        chat_threads[
            thread_id
        ] = title

    current_thread_id = (
        st.session_state.thread_id
    )

    # --------------------------------------------------------
    # Keep the currently active thread if it still belongs
    # to the user.
    # --------------------------------------------------------

    if (
        current_thread_id
        and current_thread_id not in chat_threads
    ):

        current_messages = (
            st.session_state.messages
        )

        if current_messages:

            chat_threads[
                current_thread_id
            ] = generate_title(
                current_messages
            )

    st.session_state.chat_threads = (
        chat_threads
    )


# ============================================================
# AUTH SCREEN
# ============================================================

def authenticate_user():

    st.html(
        """
        <div style="
            max-width:430px;
            margin:12vh auto 25px auto;
            text-align:center;
        ">

            <div class="auth-logo">
                ✦
            </div>

            <div class="auth-title">
                AgenticGPT
            </div>

            <div class="auth-subtitle">
                Your personal AI workspace.
            </div>

        </div>
        """
    )

    left, center, right = st.columns(
        [1, 1.05, 1]
    )

    with center:

        login_tab, signup_tab = st.tabs(
            [
                "Sign in",
                "Create account",
            ]
        )

        # ====================================================
        # LOGIN
        # ====================================================

        with login_tab:

            with st.form(
                "login_form",
                clear_on_submit=False,
            ):

                email = st.text_input(
                    "Email",
                    placeholder="you@example.com",
                )

                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                )

                submitted = st.form_submit_button(
                    "Sign in",
                    use_container_width=True,
                )

                if submitted:

                    email = email.strip()

                    if not email:

                        st.error(
                            "Please enter your email."
                        )

                    elif not password:

                        st.error(
                            "Please enter your password."
                        )

                    else:

                        success, result = login(
                            email,
                            password,
                        )

                        if success:

                            session_token = (
                                result.get(
                                    "session_token"
                                )
                            )

                            if not session_token:

                                st.error(
                                    "Login succeeded but no session token was returned."
                                )

                                st.stop()

                            # --------------------------------
                            # Store authenticated user
                            # --------------------------------

                            try:

                                set_authenticated_user(
                                    result,
                                    session_token,
                                )

                            except Exception as e:

                                st.error(
                                    str(e)
                                )

                                st.stop()

                            # --------------------------------
                            # Reload authenticated app
                            # --------------------------------

                            st.rerun()

                        else:

                            st.error(
                                result
                            )


        # ====================================================
        # SIGNUP
        # ====================================================

        with signup_tab:

            with st.form(
                "signup_form",
                clear_on_submit=False,
            ):

                username = st.text_input(
                    "Username",
                    placeholder="Choose a username",
                )

                email = st.text_input(
                    "Email",
                    placeholder="you@example.com",
                )

                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="At least 8 characters",
                )

                confirm_password = st.text_input(
                    "Confirm password",
                    type="password",
                    placeholder="Enter your password again",
                )

                submitted = st.form_submit_button(
                    "Create account",
                    use_container_width=True,
                )

                if submitted:

                    username = username.strip()

                    email = email.strip()

                    if not username:

                        st.error(
                            "Please enter a username."
                        )

                    elif not email:

                        st.error(
                            "Please enter your email."
                        )

                    elif not password:

                        st.error(
                            "Please enter a password."
                        )

                    elif len(password) < 8:

                        st.error(
                            "Password must be at least 8 characters."
                        )

                    elif password != confirm_password:

                        st.error(
                            "Passwords do not match."
                        )

                    else:

                        success, result = signup(
                            username,
                            email,
                            password,
                        )

                        if success:

                            session_token = (
                                result.get(
                                    "session_token"
                                )
                            )

                            if not session_token:

                                st.error(
                                    "Account created but no session token was returned."
                                )

                                st.stop()

                            # --------------------------------
                            # Store authenticated user
                            # --------------------------------

                            try:

                                set_authenticated_user(
                                    result,
                                    session_token,
                                )

                            except Exception as e:

                                st.error(
                                    str(e)
                                )

                                st.stop()

                            # --------------------------------
                            # Reload authenticated app
                            # --------------------------------

                            st.rerun()

                        else:

                            st.error(
                                result
                            )

    st.html(
        """
        <div class="auth-footer">
            Powered by Gemini + LangGraph
        </div>
        """
    )


# ============================================================
# SHOW AUTH SCREEN
# ============================================================

if not st.session_state.authenticated:

    authenticate_user()

    st.stop()


# ============================================================
# AUTHENTICATED USER
# ============================================================

user_id = st.session_state.user_id


# ============================================================
# INITIALIZE USER SESSION
# ============================================================

if not st.session_state.initialized:

    try:

        refresh_threads()

    except Exception as e:

        st.error(
            f"Unable to load conversations: {str(e)}"
        )

        st.stop()

    # --------------------------------------------------------
    # Existing conversations
    # --------------------------------------------------------

    if st.session_state.chat_threads:

        # ----------------------------------------------------
        # Only automatically select an existing conversation
        # if this is NOT an explicit "New Chat" action.
        # ----------------------------------------------------

        if not st.session_state.new_chat_mode:

            thread_ids = list(
                st.session_state.chat_threads.keys()
            )

            first_thread = thread_ids[0]

            st.session_state.thread_id = (
                first_thread
            )

            st.session_state.messages = (
                load_thread(
                    first_thread
                )
            )

    # --------------------------------------------------------
    # No existing conversations
    # --------------------------------------------------------

    else:

        st.session_state.thread_id = None

        st.session_state.messages = []

    st.session_state.initialized = True


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

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

    safe_username = html.escape(
        str(st.session_state.username)
    )

    safe_email = html.escape(
        str(st.session_state.email)
    )

    st.html(
        f"""
        <div class="user-info">

            <div class="user-name">
                {safe_username}
            </div>

            <div class="user-email">
                {safe_email}
            </div>

        </div>
        """
    )

    # --------------------------------------------------------
    # New Chat
    # --------------------------------------------------------

    if st.button(
        "＋  New chat",
        key="new_chat",
        use_container_width=True,
    ):

        create_new_chat()

    # --------------------------------------------------------
    # History heading
    # --------------------------------------------------------

    st.html(
        """
        <div class="history-title">
            Your chats
        </div>
        """
    )

    # --------------------------------------------------------
    # Refresh conversations
    # --------------------------------------------------------

    refresh_threads()

    thread_items = list(
        st.session_state.chat_threads.items()
    )

    # --------------------------------------------------------
    # Conversation list
    # --------------------------------------------------------

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

            col_chat, col_delete = st.columns(
                [5.5, 1],
                gap="small",
            )

            with col_chat:
                if st.button(
                    button_label,
                    key=f"thread_{thread_id}",
                    use_container_width=True,
                ):
                    switch_thread(thread_id)

            with col_delete:
                st.markdown(
                    '<div class="delete-thread-button">',
                    unsafe_allow_html=True,
                )

                if st.button(
                    "🗑",
                    key=f"delete_{thread_id}",
                    help="Delete conversation",
                    use_container_width=True,
                ):
                    st.session_state.delete_confirm_thread = thread_id
                    st.rerun()

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True,
                )

            if st.session_state.delete_confirm_thread == thread_id:

                st.markdown(
                    '<div class="delete-confirmation">'
                    '<div class="delete-confirmation-text">'
                    'Delete this conversation permanently?'
                    '</div></div>',
                    unsafe_allow_html=True,
                )

                confirm_col, cancel_col = st.columns(
                    2,
                    gap="small",
                )

                with confirm_col:
                    if st.button(
                        "Delete",
                        key=f"confirm_delete_{thread_id}",
                        use_container_width=True,
                    ):
                        delete_thread_from_ui(thread_id)

                with cancel_col:
                    if st.button(
                        "Cancel",
                        key=f"cancel_delete_{thread_id}",
                        use_container_width=True,
                    ):
                        st.session_state.delete_confirm_thread = None
                        st.rerun()

    else:

        st.caption(
            "No previous conversations"
        )

    # --------------------------------------------------------
    # Sidebar separator
    # --------------------------------------------------------

    st.markdown("---")

    # --------------------------------------------------------
    # Logout
    # --------------------------------------------------------

    st.markdown(
        '<div class="logout-button">',
        unsafe_allow_html=True,
    )

    if st.button(
        "↪  Log out",
        key="logout",
        use_container_width=True,
    ):

        logout()

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Sidebar footer
    # --------------------------------------------------------

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

        display_info = get_display_info(
            message
        )

        message_type = display_info[
            "type"
        ]

        text = display_info[
            "text"
        ]

        filename = display_info.get(
            "filename"
        )

        with st.chat_message("user"):

            if message_type == "pdf":

                st.caption(
                    f"📄 {filename}"
                )

            if text:

                st.markdown(
                    text
                )

    # ========================================================
    # AI MESSAGE
    # ========================================================

    elif isinstance(message, AIMessage):

        content = extract_text(
            message.content
        )

        if content:

            with st.chat_message(
                "assistant"
            ):

                st.markdown(
                    content
                )


# ============================================================
# CHAT INPUT
# ============================================================

chat_input = st.chat_input(
    "Message AgenticGPT...",
    accept_file=True,
    file_type=["pdf"],
)


# ============================================================
# EXTRACT CHAT INPUT
# ============================================================

user_input = None
uploaded_file = None

if chat_input:

    if isinstance(
        chat_input,
        str,
    ):

        user_input = chat_input.strip()

    else:

        user_input = (
            chat_input.text.strip()
            if chat_input.text
            else ""
        )

        if chat_input.files:

            uploaded_file = (
                chat_input.files[0]
            )


# ============================================================
# PROCESS USER INPUT
# ============================================================

if chat_input:

    # ========================================================
    # CREATE THREAD ONLY NOW
    # ========================================================

    if user_input or uploaded_file:

        try:

            current_thread_id = (
                create_thread_when_needed()
            )

        except Exception as e:

            st.error(
                f"Could not start conversation: {str(e)}"
            )

            st.stop()

        # ====================================================
        # HANDLE PDF UPLOAD
        # ====================================================

        if uploaded_file:

            upload_dir = os.path.join(
                "uploaded_pdfs",
                current_thread_id,
            )

            os.makedirs(
                upload_dir,
                exist_ok=True,
            )

            safe_filename = os.path.basename(
                uploaded_file.name
            )

            file_path = os.path.join(
                upload_dir,
                safe_filename,
            )

            try:

                # --------------------------------------------
                # Save PDF
                # --------------------------------------------

                with open(
                    file_path,
                    "wb",
                ) as f:

                    f.write(
                        uploaded_file.getbuffer()
                    )

                # --------------------------------------------
                # Index PDF
                # --------------------------------------------

                with st.spinner(
                    "Reading and indexing PDF..."
                ):

                    ingest_rag_documents(
                        file_path,
                        current_thread_id,
                        user_id,
                    )

            except Exception as e:

                st.error(
                    f"Failed to process PDF: {str(e)}"
                )

                st.stop()

        # ====================================================
        # INTERNAL MESSAGE SENT TO LANGGRAPH
        # ====================================================

        if uploaded_file:

            user_message_content = f"""
The user has uploaded a PDF named "{safe_filename}".

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
        # STORE USER MESSAGE LOCALLY
        # ====================================================

        st.session_state.messages.append(
            user_message
        )

        # ====================================================
        # DISPLAY USER MESSAGE
        # ====================================================

        with st.chat_message(
            "user"
        ):

            if uploaded_file:

                st.caption(
                    f"📄 {safe_filename}"
                )

            if user_input:

                st.markdown(
                    user_input
                )

        # ====================================================
        # ASSISTANT RESPONSE
        # ====================================================

        with st.chat_message(
            "assistant"
        ):

            with st.spinner(
                "Thinking..."
            ):

                assistant_placeholder = (
                    st.empty()
                )

                full_response = ""

                # ------------------------------------------------
                # LangGraph configuration
                # ------------------------------------------------

                config = {
                    "configurable": {
                        "thread_id":
                            current_thread_id
                    }
                }

                try:

                    # ==============================================
                    # SECURITY CHECK
                    # ==============================================

                    if not thread_belongs_to_user(
                        current_thread_id,
                        user_id,
                    ):

                        raise PermissionError(
                            "You do not have access to this conversation."
                        )

                    # ==============================================
                    # STREAM RESPONSE
                    # ==============================================

                    for (
                        message_chunk,
                        metadata,
                    ) in agenticgpt.stream(

                        {
                            "messages": [
                                user_message
                            ],

                            "thread_id":
                                current_thread_id,

                            "user_id":
                                user_id,
                        },

                        config=config,

                        stream_mode="messages",
                    ):

                        # ------------------------------------------
                        # Only process AI messages
                        # ------------------------------------------

                        if not isinstance(
                            message_chunk,
                            AIMessage,
                        ):

                            continue

                        # ------------------------------------------
                        # Extract text
                        # ------------------------------------------

                        content = extract_text(
                            message_chunk.content
                        )

                        # ------------------------------------------
                        # Ignore empty chunks
                        # ------------------------------------------

                        if not content:
                            continue

                        # ------------------------------------------
                        # Append streamed content
                        # ------------------------------------------

                        full_response += content

                        # ------------------------------------------
                        # Render streaming markdown
                        # ------------------------------------------

                        assistant_placeholder.markdown(
                            full_response + "▌"
                        )

                    # ==============================================
                    # FINAL RESPONSE
                    # ==============================================

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

        # ========================================================
        # SAVE ASSISTANT RESPONSE LOCALLY
        # ========================================================

        if full_response:

            assistant_message = AIMessage(
                content=full_response
            )

            st.session_state.messages.append(
                assistant_message
            )

        # ========================================================
        # REFRESH SIDEBAR
        # ========================================================

        refresh_threads()

        # ========================================================
        # RERUN
        # ========================================================

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