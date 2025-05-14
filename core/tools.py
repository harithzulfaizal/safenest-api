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
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    original_stdout = sys.stdout
    original_stderr = sys.stderr

    execution_exception = None
    execution_scope = {'__builtins__': __builtins__}

    try:
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            # WARNING: Running arbitrary code with exec() can be dangerous if the
            # code comes from untrusted sources. Be extremely careful.
            exec(code_string, execution_scope, execution_scope)
    except Exception as e:
        execution_exception = e
        print(f"Execution Error: {e}", file=sys.stderr)
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr

    captured_stdout = stdout_buffer.getvalue()
    captured_stderr = stderr_buffer.getvalue()

    return {
        "output": captured_stdout,
        "error": captured_stderr,
        "exception": str(execution_exception)
    }
