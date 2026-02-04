# test_hf_api.py
from gradio_client import Client

# Initialize Hugging Face client
try:
    hf_client = Client("aliarsal1512/java_comment_generator")
    print("✅ Hugging Face client initialized")
except Exception as e:
    print("❌ HF Client init failed:", e)
    hf_client = None

# Optional: a simple preprocessing function
def preprocess_code(code: str) -> str:
    # Example: strip extra spaces or line breaks
    return code.strip()

# Simple cleaning function for comments
def clean_comment(comment: str) -> str:
    # Example: remove extra newlines
    return comment.strip()

# Example Java code snippets to test
java_snippets = [
    """
    public class HelloWorld {
        public void sayHello() {
            System.out.println("Hello, World!");
        }
    }
    """,
    """
    public class Calculator {
        public int add(int a, int b) {
            return a + b;
        }
    }
    """
]

if hf_client:
    for idx, code in enumerate(java_snippets, start=1):
        processed_code = preprocess_code(code)
        try:
            # Call the HF Space API
            result = hf_client.predict(
                processed_code,
                api_name="/generate_comment"
            )
            comment = clean_comment(result)
            print(f"\nSnippet {idx} comment:\n{comment}")
        except Exception as e:
            print(f"❌ Error generating comment for snippet {idx}: {e}")
