"""
Level 2 Agent - Internet Search Agent
An agent that performs internet searches using Tavily API.
"""

import os
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from tavily import TavilyClient

# Load environment variables
load_dotenv()

def get_llm():
    """Initialize and return the appropriate LLM based on available API keys."""
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    
    if openai_key:
        print("Using OpenAI API")
        return ChatOpenAI(model="gpt-4", temperature=0)
    elif gemini_key:
        print("Using Google Gemini API")
        return ChatGoogleGenerativeAI(model="models/gemini-2.0-flash-lite", google_api_key=gemini_key, temperature=0)
    elif groq_key:
        print("Using Groq API")
        # Groq uses OpenAI-compatible API
        return ChatOpenAI(
            model="llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_key,
            temperature=0
        )
    else:
        raise ValueError("No API key provided. Please set OPENAI_API_KEY, GEMINI_API_KEY, or GROQ_API_KEY in .env file")

def tavily_search(query: str) -> str:
    """
    Performs an internet search using Tavily API.
    
    Args:
        query: The search query
        
    Returns:
        Search results as a string
    """
    print("\n[TOOL INVOKED] tavily_search()")
    print(f"   Query: {query}")
    
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not tavily_key:
        return "Error: TAVILY_API_KEY not set in environment variables"
    
    try:
        client = TavilyClient(api_key=tavily_key)
        response = client.search(query=query, max_results=5)
        
        results = []
        if 'results' in response:
            for result in response['results']:
                title = result.get('title', 'No title')
                url = result.get('url', 'No URL')
                content = result.get('content', 'No content')
                results.append(f"Title: {title}\nURL: {url}\nContent: {content}\n")
        
        output = "\n---\n".join(results) if results else "No results found"
        print(f"   Found {len(response.get('results', []))} results")
        return output
    except Exception as e:
        error_msg = f"Error performing search: {str(e)}"
        print(f"   {error_msg}")
        return error_msg

def create_tools():
    """Create tools for the agent."""
    return [
        Tool(
            name="tavily_search",
            func=tavily_search,
            description="Performs an internet search using Tavily API. Use this tool to search for current information, news, facts, or any topic. Input should be a search query string."
        ),
    ]

def main():
    """Main function to run the Level 2 agent."""
    print("=" * 60)
    print("Level 2 Agent - Internet Search Agent")
    print("=" * 60)
    print("\nThis agent performs internet searches to answer your questions.")
    print("Type 'exit' to quit.\n")
    
    # Check for Tavily API key
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not tavily_key:
        print("Warning: TAVILY_API_KEY not set. Internet search will not work.")
        print("Please set TAVILY_API_KEY in your .env file.\n")
    
    try:
        llm = get_llm()
        tools = create_tools()
        
        # Create ReAct prompt template
        prompt = PromptTemplate.from_template("""
You are a helpful assistant that answers questions by searching the internet.

You have access to the following tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}
""")
        
        # Create ReAct agent
        agent = create_react_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        
        while True:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye!")
                break
            
            if not user_input:
                continue
            
            try:
                result = agent_executor.invoke({"input": user_input})
                print(f"\nAgent: {result['output']}")
            except Exception as e:
                print(f"\nError: {str(e)}")
                
    except ValueError as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")

if __name__ == "__main__":
    main()

