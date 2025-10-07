from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import sqlite3
import os

load_dotenv()

os.environ["GOOGLE_API_KEY"] = "AIzaSyCi6AKnl826Ql_4MotHHAVtl_-_aAmAui4"

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    google_api_key=os.environ["GOOGLE_API_KEY"],
    convert_system_message_to_human=True
)
print("✓ Using model: gemini-2.0-flash-exp")


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state['messages']
    response = llm.invoke(messages)
    return {"messages": [response]}

# Database connection
conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)

# Create table for chat metadata if it doesn't exist
def init_chat_metadata_table():
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_metadata (
            thread_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            summary TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

init_chat_metadata_table()

# Checkpointer
checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)


def retrieve_all_threads():
    """Retrieve all thread IDs (legacy function)"""
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])
    return list(all_threads)


def retrieve_user_threads(user_id):
    """Retrieve all threads for a specific user with summaries"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT thread_id, summary, created_at 
        FROM chat_metadata 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (user_id,))
    
    threads = []
    for row in cursor.fetchall():
        threads.append({
            'thread_id': row[0],
            'summary': row[1],
            'created_at': row[2]
        })
    
    return threads


def save_chat_summary(thread_id, summary, user_id):
    """Save or update chat summary for a thread"""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO chat_metadata (thread_id, user_id, summary)
        VALUES (?, ?, ?)
    ''', (thread_id, user_id, summary))
    conn.commit()


def get_chat_summary(thread_id):
    """Get chat summary for a specific thread"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT summary FROM chat_metadata WHERE thread_id = ?
    ''', (thread_id,))
    
    result = cursor.fetchone()
    return result[0] if result else None


def delete_user_thread(thread_id, user_id):
    """Delete a thread (optional feature for future)"""
    cursor = conn.cursor()
    # First verify the thread belongs to the user
    cursor.execute('''
        SELECT user_id FROM chat_metadata WHERE thread_id = ?
    ''', (thread_id,))
    
    result = cursor.fetchone()
    if result and result[0] == user_id:
        cursor.execute('DELETE FROM chat_metadata WHERE thread_id = ?', (thread_id,))
        conn.commit()
        return True
    return False