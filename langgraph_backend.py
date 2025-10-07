from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
import os

load_dotenv()

# Set API key (remove from code in production!)
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
    """
    Process the conversation with full message history
    """
    messages = state['messages']
    
    # The state already contains the full conversation history
    # thanks to add_messages and the checkpointer
    response = llm.invoke(messages)
    
    return {'messages': [response]}


# Create graph with memory
checkpointer = MemorySaver()
graph = StateGraph(ChatState)

graph.add_node('chat_node', chat_node)
graph.add_edge(START, 'chat_node')
graph.add_edge('chat_node', END)

chatbot = graph.compile(checkpointer=checkpointer)

# Test the chatbot (optional)
if __name__ == "__main__":
    from langchain_core.messages import HumanMessage
    
    config = {'configurable': {'thread_id': 'test-thread'}}
    
    # First message
    response1 = chatbot.invoke(
        {'messages': [HumanMessage(content="My name is Alice")]},
        config=config
    )
    print("Bot:", response1['messages'][-1].content)
    
    # Second message - should remember
    response2 = chatbot.invoke(
        {'messages': [HumanMessage(content="What's my name?")]},
        config=config
    )
    print("Bot:", response2['messages'][-1].content)