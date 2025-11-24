"""
Level 3 Agent - RAG Agent with PDF Processing
A RAG agent that processes PDF files using ChromaDB.
"""

import os
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Load environment variables
load_dotenv()

DATA_FOLDER = Path(__file__).parent / "data"
INDEX_FOLDER = Path(__file__).parent / "index"
HASH_FILE = Path(__file__).parent / "file_hashes.json"

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
    """Load stored file hashes."""
    if HASH_FILE.exists():
        try:
            with open(HASH_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_hashes(hashes: dict):
    """Save file hashes."""
    with open(HASH_FILE, 'w') as f:
        json.dump(hashes, f, indent=2)

def has_files_changed() -> bool:
    """Check if any files have been added, deleted, or modified."""
    current_hashes = get_all_file_hashes()
    stored_hashes = load_hashes()
    
    # Check if files were added or modified
    for filename, current_hash in current_hashes.items():
        if filename not in stored_hashes or stored_hashes[filename] != current_hash:
            return True
    
    # Check if files were deleted
    for filename in stored_hashes:
        if filename not in current_hashes:
            return True
    
    return False

def get_embeddings():
    """Get the appropriate embeddings model."""
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    if openai_key:
        return OpenAIEmbeddings()
    elif gemini_key:
        return GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=gemini_key)
    else:
        # Fallback to OpenAI (will fail if no key, but that's expected)
        return OpenAIEmbeddings()

def build_index():
    """Build or rebuild the ChromaDB index from PDF files."""
    print("\n[TOOL INVOKED] Building/rebuilding index...")
    
    # Ensure folders exist
    DATA_FOLDER.mkdir(exist_ok=True)
    INDEX_FOLDER.mkdir(exist_ok=True)
    
    # Load all PDF files
    documents = []
    pdf_files = list(DATA_FOLDER.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in data folder.")
        return None
    
    print(f"Found {len(pdf_files)} PDF file(s)")
    
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
    
    # Split documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(documents)
    print(f"Split into {len(splits)} chunks")
    
    # Create embeddings and vector store
    embeddings = get_embeddings()
    
    # Remove old index if it exists
    if INDEX_FOLDER.exists():
        import shutil
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
    """Load existing index."""
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
        print("\n[WARNING]  Files have changed. Rebuilding index...")
        return build_index()
    
    # Try to load existing index
    vectorstore = load_index()
    if vectorstore is None:
        print("\n[WARNING] No existing index found. Building new index...")
        return build_index()
    
    return vectorstore

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

def search_documents(query: str) -> str:
    """
    Search the document index for relevant information.
    
    Args:
        query: The search query
        
    Returns:
        Relevant document chunks as a string
    """
    print("\n[TOOL INVOKED] search_documents()")
    print(f"   Query: {query}")
    
    vectorstore = get_vectorstore()
    if vectorstore is None:
        return "Error: No documents indexed. Please add PDF files to the data folder."
    
    try:
        # Search for relevant documents
        docs = vectorstore.similarity_search(query, k=3)
        
        results = []
        for i, doc in enumerate(docs, 1):
            content = doc.page_content
            source = doc.metadata.get('source', 'Unknown')
            results.append(f"[Document {i} from {Path(source).name}]\n{content}\n")
        
        output = "\n---\n".join(results) if results else "No relevant documents found."
        print(f"   Found {len(docs)} relevant document(s)")
        return output
    except Exception as e:
        error_msg = f"Error searching documents: {str(e)}"
        print(f"   {error_msg}")
        return error_msg

def create_tools():
    """Create tools for the agent."""
    return [
        Tool(
            name="search_documents",
            func=search_documents,
            description="Searches the indexed PDF documents for relevant information. Use this tool to answer questions based on the documents in the data folder. Input should be a search query string."
        ),
    ]

def main():
    """Main function to run the Level 3 agent."""
    print("=" * 60)
    print("Level 3 Agent - RAG Agent with PDF Processing")
    print("=" * 60)
    print("\nThis agent answers questions based on PDF documents in the data folder.")
    print("The index is automatically rebuilt when files are added, deleted, or modified.")
    print("Type 'exit' to quit.\n")
    
    # Initialize vectorstore on startup
    print("Initializing document index...")
    get_vectorstore()
    
    try:
        llm = get_llm()
        tools = create_tools()
        
        # Create ReAct prompt template
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
            
            # Check for file changes before each query
            if has_files_changed():
                print("\n[WARNING]  Files have changed. Rebuilding index...")
                get_vectorstore()
            
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

