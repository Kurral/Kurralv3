"""
Level 1 Agent - Short Form to Full Form Converter
A ReAct agent that uses tools to convert short forms to full forms.
"""

import os
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from tools import get_full_form, multiply, add
from Kurral_tester.agent_decorator import trace_agent, trace_agent_invoke

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

def create_tools():
    """Create tools for the agent."""
    return [
        Tool(
            name="get_full_form",
            func=get_full_form,
            description="Converts a short form abbreviation to its full form. Input should be a short form like 'AI', 'ML', 'API', etc."
        ),
        Tool(
            name="multiply",
            func=multiply,
            description="Multiplies two numbers. Takes two numbers as input separated by comma, e.g., '5,3'"
        ),
        Tool(
            name="add",
            func=add,
            description="Adds two numbers. Takes two numbers as input separated by comma, e.g., '5,3'"
        ),
    ]

@trace_agent()
def main():
    """Main function to run the Level 1 agent."""
    print("=" * 60)
    print("Level 1 Agent - Short Form to Full Form Converter")
    print("=" * 60)
    print("\nThis agent converts short forms to full forms.")
    print("Available short forms: AI, ML, API, HTTP, URL, CPU, GPU, RAM, SQL, JSON, XML, HTML, CSS, JS, PDF, CSV, REST, SOAP, IDE, OS")
    print("\nYou can also ask for calculations (multiplication or addition).")
    print("Type 'exit' to quit.\n")
    
    try:
        llm = get_llm()
        tools = create_tools()
        
        # Create ReAct prompt template
        prompt = PromptTemplate.from_template("""
You are a helpful assistant that converts short forms to full forms and performs calculations.

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
Only give the final answer based on the output provided by the tools, no need to validate the answer.
Final Answer: the final answer to the original input question
IMPORTANT: When you have the answer from the tool. go directly to final answer section and give the answer.
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
                result = trace_agent_invoke(agent_executor, {"input": user_input}, llm=llm)
                print(f"\nAgent: {result['output']}")
            except Exception as e:
                print(f"\nError: {str(e)}")
                
    except ValueError as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")

if __name__ == "__main__":
    main()

