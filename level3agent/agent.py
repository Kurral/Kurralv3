"""
Level 3 Agent - RAG Agent with PDF Processing

A RAG agent that processes PDF files using ChromaDB and sends email summaries
after successful responses.
"""
## test
import hashlib
import json
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from send_email import send_email

# Load environment variables
load_dotenv()

# Constants
DATA_FOLDER = Path(__file__).parent / "data"
INDEX_FOLDER = Path(__file__).parent / "index"
HASH_FILE = Path(__file__).parent / "file_hashes.json"

# Configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
SEARCH_RESULTS_COUNT = 3


def get_file_hash(file_path: Path) -> str:
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_all_file_hashes() -> dict:
    """Get hashes of all PDF files in the data folder."""
    hashes = {}
    if DATA_FOLDER.exists():
        for pdf_file in DATA_FOLDER.glob("*.pdf"):
            hashes[str(pdf_file.name)] = get_file_hash(pdf_file)
    return hashes


def load_hashes() -> dict:
    """Load stored file hashes from disk."""
    if not HASH_FILE.exists():
        return {}
    
    try:
        with open(HASH_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_hashes(hashes: dict) -> None:
    """Save file hashes to disk."""
    with open(HASH_FILE, 'w') as f:
        json.dump(hashes, f, indent=2)


def has_files_changed() -> bool:
    """Check if any PDF files have been added, deleted, or modified."""
    current_hashes = get_all_file_hashes()
    stored_hashes = load_hashes()
    
    # Check if files were added or modified
    for filename, current_hash in current_hashes.items():
        if filename not in stored_hashes or stored_hashes[filename] != current_hash:
            return True
    
    # Check if files were deleted
    if any(filename not in current_hashes for filename in stored_hashes):
        return True
    
    return False


def get_embeddings():
    """
    Get the appropriate embeddings model based on available API keys.
    
    Supports OpenAI or Gemini embeddings.
    """
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    # Use OpenAI if available
    if openai_key:
        print("✓ Using OpenAI embeddings")
        return OpenAIEmbeddings()
    
    # Use Gemini if available
    elif gemini_key:
        print("✓ Using Gemini embeddings")
        return GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=gemini_key
        )
    
    # No embedding key found
    else:
        raise ValueError(
            "❌ No embedding API key found!\n\n"
            "Embeddings are required to search PDF documents. Please set:\n"
            "  • OPENAI_API_KEY=sk-... (for OpenAI embeddings)\n"
            "  • GEMINI_API_KEY=... (for Gemini embeddings)\n"
        )


def build_index():
    """Build or rebuild the ChromaDB index from PDF files."""
    print("\n[TOOL INVOKED] Building/rebuilding index...")
    
    # Ensure folders exist
    DATA_FOLDER.mkdir(exist_ok=True)
    INDEX_FOLDER.mkdir(exist_ok=True)
    
    # Load all PDF files
    pdf_files = list(DATA_FOLDER.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found in data folder.")
        return None
    
    print(f"Found {len(pdf_files)} PDF file(s)")
    
    documents = []
    for pdf_file in pdf_files:
        print(f"  Processing: {pdf_file.name}")
        try:
            loader = PyPDFLoader(str(pdf_file))
            docs = loader.load()
            documents.extend(docs)
        except Exception as e:
            print(f"  Error loading {pdf_file.name}: {str(e)}")
    
    if not documents:
        print("No documents loaded.")
        return None
    
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    splits = text_splitter.split_documents(documents)
    print(f"Split into {len(splits)} chunks")
    
    # Create embeddings and vector store
    embeddings = get_embeddings()
    
    # Remove old index if it exists
    if INDEX_FOLDER.exists():
        shutil.rmtree(INDEX_FOLDER)
    
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=str(INDEX_FOLDER)
    )
    
    # Save current file hashes
    save_hashes(get_all_file_hashes())
    
    print("Index built successfully!")
    return vectorstore


def load_index():
    """Load existing index from disk."""
    if not INDEX_FOLDER.exists():
        return None
    
    try:
        embeddings = get_embeddings()
        vectorstore = Chroma(
            persist_directory=str(INDEX_FOLDER),
            embedding_function=embeddings
        )
        return vectorstore
    except Exception as e:
        print(f"Error loading index: {str(e)}")
        return None


def get_vectorstore():
    """Get vectorstore, rebuilding if necessary."""
    # Check if files have changed
    if has_files_changed():
        print("\n[WARNING] Files have changed. Rebuilding index...")
        return build_index()
    
    # Try to load existing index
    vectorstore = load_index()
    if vectorstore is None:
        print("\n[WARNING] No existing index found. Building new index...")
        return build_index()
    
    return vectorstore


def get_llm():
    """
    Initialize and return the appropriate LLM based on available API keys.
    
    User should have exactly ONE LLM key set. Supports OpenAI or Gemini.
    """
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    # Count how many keys are set
    keys_set = sum([bool(openai_key), bool(gemini_key)])
    
    if keys_set == 0:
        raise ValueError(
            "❌ No LLM API key found!\n\n"
            "Please set exactly ONE of the following in your .env file:\n"
            "  • OPENAI_API_KEY=sk-...\n"
            "  • GEMINI_API_KEY=...\n"
        )
    
    if keys_set > 1:
        raise ValueError(
            "❌ Multiple LLM API keys found!\n\n"
            "Please set exactly ONE LLM API key. Found:\n"
            f"{'  • OPENAI_API_KEY (set)' if openai_key else ''}\n"
            f"{'  • GEMINI_API_KEY (set)' if gemini_key else ''}\n\n"
            "Leave the other key empty in your .env file."
        )
    
    # Exactly one key is set - use it
    if openai_key:
        print("✓ Using OpenAI for LLM")
        return ChatOpenAI(model="gpt-4", temperature=0)
    
    elif gemini_key:
        print("✓ Using Gemini for LLM")
        return ChatGoogleGenerativeAI(
            model="models/gemini-2.0-flash-lite",
            google_api_key=gemini_key,
            temperature=0
        )
    
    # This shouldn't happen, but just in case
    raise ValueError("Unexpected error: Could not determine which LLM to use.")


def search_documents(query: str) -> str:
    """
    Search the document index for relevant information.
    
    Args:
        query: The search query string
        
    Returns:
        Relevant document chunks as a formatted string
    """
    print("\n[TOOL INVOKED] search_documents()")
    print(f"   Query: {query}")
    
    vectorstore = get_vectorstore()
    if vectorstore is None:
        return "Error: No documents indexed. Please add PDF files to the data folder."
    
    try:
        # Search for relevant documents
        docs = vectorstore.similarity_search(query, k=SEARCH_RESULTS_COUNT)
        
        if not docs:
            return "No relevant documents found."
        
        results = []
        for i, doc in enumerate(docs, 1):
            content = doc.page_content
            source = doc.metadata.get('source', 'Unknown')
            filename = Path(source).name
            results.append(f"[Document {i} from {filename}]\n{content}\n")
        
        output = "\n---\n".join(results)
        print(f"   Found {len(docs)} relevant document(s)")
        return output
    
    except Exception as e:
        error_msg = f"Error searching documents: {str(e)}"
        print(f"   {error_msg}")
        return error_msg


def create_tools():
    """Create and return tools for the agent."""
    return [
        Tool(
            name="search_documents",
            func=search_documents,
            description=(
                "Searches the indexed PDF documents for relevant information. "
                "Use this tool to answer questions based on the documents in the data folder. "
                "Input should be a search query string."
            )
        ),
    ]


def get_receiver_email() -> str:
    """Get recipient email - defaults to jayjani482001@gmail.com."""
    return "jayjani482001@gmail.com"


def send_summary_email(question: str, summary: str, receiver_email: str) -> None:
    """
    Send an email with the agent summary.
    
    Args:
        question: The original question asked
        summary: The agent's summary response
        receiver_email: Email address to send to
    """
    # Create subject line (truncate if too long)
    if len(question) > 50:
        email_subject = f"Agent Summary: {question[:50]}..."
    else:
        email_subject = f"Agent Summary: {question}"
    
    # Format email body
    email_body = f"""Question: {question}

Summary:
{summary}

---
Generated by Level 3 Agent
"""
    
    try:
        send_email(receiver_email, email_subject, email_body, verbosity=True)
    except Exception as email_error:
        print(f"\n[WARNING] Failed to send email: {str(email_error)}")


def create_agent_executor(llm, tools):
    """Create and configure the ReAct agent executor."""
    prompt = PromptTemplate.from_template("""
You are a helpful assistant that answers questions based on PDF documents.

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
    
    agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


def process_user_query(agent_executor, user_input: str) -> None:
    """Process a user query and send email summary if successful."""
    try:
        result = agent_executor.invoke({"input": user_input})
        summary = result['output']
        print(f"\nAgent: {summary}")
        
        # Send email after successful summary
        receiver_email = get_receiver_email()
        send_summary_email(user_input, summary, receiver_email)
    
    except Exception as e:
        print(f"\nError: {str(e)}")


def validate_configuration():
    """
    Validate that both LLM and embeddings are properly configured.
    
    Rules:
    - Exactly ONE LLM key must be set (OPENAI_API_KEY or GEMINI_API_KEY)
    - The same key is used for both LLM and embeddings
    """
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    # Check which keys are set
    has_openai = bool(openai_key)
    has_gemini = bool(gemini_key)
    
    llm_key_count = sum([has_openai, has_gemini])
    
    # Validate exactly one LLM key is set
    if llm_key_count == 0:
        raise ValueError(
            "❌ No LLM API key found!\n\n"
            "Please set exactly ONE of the following in your .env file:\n"
            "  • OPENAI_API_KEY=sk-...\n"
            "  • GEMINI_API_KEY=...\n"
        )
    
    if llm_key_count > 1:
        set_keys = []
        if has_openai:
            set_keys.append("OPENAI_API_KEY")
        if has_gemini:
            set_keys.append("GEMINI_API_KEY")
        
        raise ValueError(
            f"❌ Multiple LLM keys found ({llm_key_count})!\n\n"
            f"Found: {', '.join(set_keys)}\n"
            "Please set exactly ONE LLM API key. Leave the other empty in your .env file."
        )


def main():
    """Main function to run the Level 3 agent."""
    print("=" * 60)
    print("Level 3 Agent - RAG Agent with PDF Processing")
    print("=" * 60)
    print("\nThis agent answers questions based on PDF documents in the data folder.")
    print("The index is automatically rebuilt when files are added, deleted, or modified.")
    print("Type 'exit' to quit.\n")
    
    # Validate configuration before starting
    try:
        validate_configuration()
    except ValueError as e:
        print(f"\n{str(e)}\n")
        return
    
    # Initialize LLM and embeddings
    try:
        llm = get_llm()
        # Test embeddings can be created
        _ = get_embeddings()
    except ValueError as e:
        print(f"\n{str(e)}\n")
        return
    
    # Initialize vectorstore on startup
    print("\nInitializing document index...")
    try:
        get_vectorstore()
    except Exception as e:
        print(f"\nError initializing index: {str(e)}\n")
        return
    
    try:
        tools = create_tools()
        agent_executor = create_agent_executor(llm, tools)
        
        # Main interaction loop
        while True:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye!")
                break
            
            if not user_input:
                continue
            
            # Check for file changes before each query
            if has_files_changed():
                print("\n[WARNING] Files have changed. Rebuilding index...")
                get_vectorstore()
            
            process_user_query(agent_executor, user_input)
    
    except ValueError as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")


if __name__ == "__main__":
    main()
