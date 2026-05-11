from config import config
from src.graph import app
import json

def main():
    # Use the doc_id from the config or a default one for testing
    doc_id = config.doc_id
    
    if not doc_id:
        print("Error: No DOC_ID found in .env file.")
        return

    print(f"Starting analyst agent for document: {doc_id}")
    
    # Initialize the state
    initial_state = {
        "doc_id": doc_id,
        "course_structure": None,
        "is_valid": False,
        "errors": []
    }
    
    # Run the graph
    final_state = app.invoke(initial_state)
    
    # Print the results
    if final_state.get("is_valid"):
        print("\n--- Course Structure Inferred ---")
        structure = final_state.get("course_structure")
        if structure:
            # Pydantic models can be converted to dict for printing
            print(json.dumps(structure.model_dump(), indent=2, ensure_ascii=False))
    else:
        print("\n--- Inference Failed ---")
        for error in final_state.get("errors", []):
            print(f"Error: {error}")

if __name__ == "__main__":
    main()
