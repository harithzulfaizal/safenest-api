import io
import sys
from contextlib import redirect_stdout, redirect_stderr

def execute_python_code(code_string: str):
    """
    Executes a string containing Python code.
    Use only the Python standard library and built-in modules.

    Args:
        code_string: A string containing the Python code to execute.

    Returns:
        - The standard output captured during execution (as a string).
        - The standard error captured during execution (as a string).
        - None if execution was successful, or the Exception object if an error occurred.
    """
    code_string = code_string.replace("```python", "").replace("```tool_code", "").replace("```", "").strip()
    # Create buffers to capture stdout and stderr
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    # Keep track of the original stdout and stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    execution_exception = None
    execution_scope = {'__builtins__': __builtins__}


    try:
        # Redirect stdout and stderr to our buffers
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            # Use exec() to execute the code string
            # Pass empty dictionaries for globals and locals for a sandboxed environment,
            # or pass specific dictionaries if needed.
            # WARNING: Running arbitrary code with exec() can be dangerous if the
            # code comes from untrusted sources. Be extremely careful.
            exec(code_string, execution_scope, execution_scope)# Using empty dicts for globals/locals

    except Exception as e:
        # Capture any exception that occurs during execution
        execution_exception = e
        # Ensure the error message is also captured in the stderr buffer
        print(f"Execution Error: {e}", file=sys.stderr)
    finally:
        # Restore original stdout and stderr (though contextlib should handle this)
        sys.stdout = original_stdout
        sys.stderr = original_stderr

    # Get the captured output and errors
    captured_stdout = stdout_buffer.getvalue()
    captured_stderr = stderr_buffer.getvalue()

    return {
        "output": captured_stdout,
        "error": captured_stderr,
        "exception": str(execution_exception)
    }
