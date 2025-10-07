import streamlit as st
from langgraph_database_backend import chatbot, retrieve_user_threads, save_chat_summary, get_chat_summary
from langchain_core.messages import HumanMessage
import uuid

# **************************************** utility functions *************************

def generate_thread_id():
    thread_id = str(uuid.uuid4())
    return thread_id

def generate_user_id():
    """Generate or retrieve user ID from browser session"""
    user_id = str(uuid.uuid4())
    return user_id

def generate_chat_summary(first_message):
    """Generate a short summary from the first message"""
    # Truncate to first 50 characters or first sentence
    summary = first_message.strip()
    if len(summary) > 50:
        summary = summary[:47] + "..."
    elif not summary:
        summary = "New Conversation"
    return summary

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    st.session_state['message_history'] = []
    st.session_state['current_chat_summary'] = None
    # Note: We'll add the thread to the list after first message

def add_thread_with_summary(thread_id, summary):
    """Add thread with its summary to the session state"""
    if not any(t['thread_id'] == thread_id for t in st.session_state['chat_threads']):
        st.session_state['chat_threads'].insert(0, {
            'thread_id': thread_id,
            'summary': summary
        })
        # Save to database
        save_chat_summary(thread_id, summary, st.session_state['user_id'])

def load_conversation(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    return state.values.get('messages', [])


# **************************************** Session Setup ******************************

# Initialize user_id (unique per browser session)
if 'user_id' not in st.session_state:
    # Check if user_id exists in query params (for persistence across page reloads)
    query_params = st.query_params
    if 'user_id' in query_params:
        st.session_state['user_id'] = query_params['user_id']
    else:
        st.session_state['user_id'] = generate_user_id()
        # Set query param to persist user_id
        st.query_params['user_id'] = st.session_state['user_id']

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'current_chat_summary' not in st.session_state:
    st.session_state['current_chat_summary'] = None

if 'chat_threads' not in st.session_state:
    # Retrieve only this user's threads
    st.session_state['chat_threads'] = retrieve_user_threads(st.session_state['user_id'])


# **************************************** Sidebar UI *********************************

st.sidebar.title('LangGraph Chatbot')

if st.sidebar.button('➕ New Chat'):
    reset_chat()

st.sidebar.header('My Conversations')

# Display chats with summaries
if st.session_state['chat_threads']:
    for chat in st.session_state['chat_threads']:
        thread_id = chat['thread_id']
        summary = chat['summary']
        
        # Highlight current chat
        button_label = f"💬 {summary}"
        if thread_id == st.session_state['thread_id']:
            button_label = f"**▶ {summary}**"
        
        if st.sidebar.button(button_label, key=f"chat_{thread_id}"):
            st.session_state['thread_id'] = thread_id
            st.session_state['current_chat_summary'] = summary
            messages = load_conversation(thread_id)

            temp_messages = []
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    role = 'user'
                else:
                    role = 'assistant'
                temp_messages.append({'role': role, 'content': msg.content})

            st.session_state['message_history'] = temp_messages
            st.rerun()
else:
    st.sidebar.info("No conversations yet. Start a new chat!")

# Display user info (for debugging - remove in production)
with st.sidebar.expander("ℹ️ Session Info"):
    st.caption(f"User ID: {st.session_state['user_id'][:8]}...")
    st.caption(f"Thread ID: {st.session_state['thread_id'][:8]}...")


# **************************************** Main UI ************************************

# Display current chat summary as title
if st.session_state['current_chat_summary']:
    st.title(f"💬 {st.session_state['current_chat_summary']}")
else:
    st.title("💬 New Conversation")

# Loading the conversation history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

user_input = st.chat_input('Type your message here...')

if user_input:
    # Add user message to history
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.markdown(user_input)

    # Generate summary from first message if this is a new chat
    if st.session_state['current_chat_summary'] is None:
        summary = generate_chat_summary(user_input)
        st.session_state['current_chat_summary'] = summary
        add_thread_with_summary(st.session_state['thread_id'], summary)

    CONFIG = {
        "configurable": {"thread_id": st.session_state["thread_id"]},
        "metadata": {
            "thread_id": st.session_state["thread_id"],
            "user_id": st.session_state["user_id"]
        },
        "run_name": "chat_turn",
    }

    # Get AI response
    with st.chat_message('assistant'):
        ai_message = st.write_stream(
            message_chunk.content for message_chunk, metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode='messages'
            )
        )

    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})