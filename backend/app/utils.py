# app/utils.py
import javalang
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import current_app # To access app.hf_pipeline

def preprocess_code(code: str) -> str:
    # ... (your preprocess_code function)
    return (
        code.replace('\t', ' ')
        .replace('\n', ' ')
        .replace('\r', ' ')
        .replace('  ', ' ')
        .strip()
    )


def wrap_code_if_needed(java_code: str) -> tuple[str, bool]:
    """
    Wrap Java code in a class if it doesn't have one.
    Returns: (wrapped_code, was_wrapped)
    """
    stripped = java_code.strip()
    
    # Check if code already starts with a class declaration
    if (stripped.startswith('class ') or 
        stripped.startswith('public class ') or 
        stripped.startswith('private class ') or 
        stripped.startswith('protected class ') or
        stripped.startswith('abstract class ') or
        stripped.startswith('final class ')):
        return java_code, False
    
    # Try parsing as-is first
    try:
        javalang.parse.parse(java_code)
        return java_code, False
    except javalang.parser.JavaSyntaxError as e:
        # Check if error is "expected type declaration" at line 1
        error_line = 1
        if e.at:
            if isinstance(e.at, javalang.tokenizer.Position):
                error_line = e.at.line
            elif hasattr(e.at, 'position') and e.at.position:
                error_line = e.at.position.line
        
        error_desc = e.description.lower() if e.description else ""
        is_type_declaration_error = (
            "expected type declaration" in error_desc or
            ("expected" in error_desc and "declaration" in error_desc)
        )
        
        # If error is at line 1 and is about type declaration, wrap in class
        if error_line == 1 and is_type_declaration_error:
            try:
                wrapped_code = f"public class nan {{\n{java_code}\n}}"
                # Verify the wrapped code parses correctly
                javalang.parse.parse(wrapped_code)
                return wrapped_code, True
            except:
                pass
        
        # For other errors, still try wrapping if it doesn't start with class
        try:
            wrapped_code = f"public class nan {{\n{java_code}\n}}"
            javalang.parse.parse(wrapped_code)
            return wrapped_code, True
        except:
            pass
        
        # If wrapping doesn't help, return original and let caller handle the error
        return java_code, False


def format_ast(java_code: str) -> str: #
    # ... (your format_ast function)
    # Make sure to handle imports like javalang at the top of this file
    try:
        # Wrap code in class if needed
        wrapped_code, was_wrapped = wrap_code_if_needed(java_code)
        tree = javalang.parse.parse(wrapped_code)
        
        # First pass: collect all classes and their inheritance relationships
        class_nodes_map = {}
        inheritance_map = {}  # Maps parent class name -> list of child class names
        child_to_parent = {}  # Maps child class name -> parent class name
        root_classes = []  # Classes that don't extend anything (or extend external classes)
        
        for _, class_node in tree.filter(javalang.tree.ClassDeclaration):
            class_name = class_node.name
            class_nodes_map[class_name] = class_node
            
            # Check if class extends another class
            if hasattr(class_node, 'extends') and class_node.extends:
                # Get the superclass name
                parent_name = None
                if hasattr(class_node.extends, 'name'):
                    parent_name = class_node.extends.name
                elif isinstance(class_node.extends, list) and len(class_node.extends) > 0:
                    # Sometimes extends is a list
                    parent_name = class_node.extends[0].name if hasattr(class_node.extends[0], 'name') else str(class_node.extends[0])
                else:
                    parent_name = str(class_node.extends)
                
                # Check if parent class exists in our code
                if parent_name and parent_name in class_nodes_map:
                    # Parent is in our code, add to inheritance map
                    if parent_name not in inheritance_map:
                        inheritance_map[parent_name] = []
                    inheritance_map[parent_name].append(class_name)
                    child_to_parent[class_name] = parent_name
                else:
                    # Parent is external, treat as root class
                    root_classes.append(class_name)
            else:
                # No extends, this is a root class
                root_classes.append(class_name)
        
        output = ['<div class="ast-tree">']
        
        # Helper function to render a class and its children recursively
        def render_class_recursive(class_name, indent_level=0):
            if class_name not in class_nodes_map:
                return
            
            class_node = class_nodes_map[class_name]
            indent = "    " * indent_level
            prefix = "└─ " if indent_level > 0 else ""
            
            # Show inheritance info
            extends_info = ""
            if hasattr(class_node, 'extends') and class_node.extends:
                if hasattr(class_node.extends, 'name'):
                    parent_name = class_node.extends.name
                elif isinstance(class_node.extends, list) and len(class_node.extends) > 0:
                    parent_name = class_node.extends[0].name if hasattr(class_node.extends[0], 'name') else str(class_node.extends[0])
                else:
                    parent_name = str(class_node.extends)
                extends_info = f" extends {parent_name}"
            
            output.append(
                f'<div class="ast-class" data-class="{class_name}" '
                f'onclick="showClassComments(\'{class_name}\')">'
                f'{indent}{prefix}📦 Class: {class_name}{extends_info}'
                '</div>'
            )
            
            # Render fields
            if class_node.fields:
                field_indent = indent + ("    " if indent_level > 0 else "")
                output.append(f'<div class="ast-section">{field_indent}├─ 🟣 Fields:')
                for field in class_node.fields:
                    modifiers = " ".join(field.modifiers) if field.modifiers else ""
                    field_type = field.type.name if field.type else "Unknown"
                    for declarator in field.declarators:
                        output.append(
                            f'<div class="ast-field">{field_indent}│   ├─ {modifiers} {field_type} {declarator.name}</div>'
                        )
                output.append('</div>')
            
            # Render methods
            if class_node.methods:
                method_indent = indent + ("    " if indent_level > 0 else "")
                output.append(f'<div class="ast-section">{method_indent}└─ 🔧 Methods:')
                for i, method in enumerate(class_node.methods):
                    is_last_method = i == len(class_node.methods) - 1
                    method_prefix = "    " if is_last_method else "│   "

                    modifiers = " ".join(method.modifiers) if method.modifiers else ""
                    return_type = method.return_type.name if method.return_type else "void"
                    params = ", ".join([f"{p.type.name} {p.name}" for p in method.parameters]) if method.parameters else ""

                    output.append(
                        f'<div class="ast-method" data-class="{class_name}" data-method="{method.name}" '
                        f'onclick="showMethodComments(\'{class_name}\', \'{method.name}\')">'
                        f'{method_indent}    {method_prefix} {"└─" if is_last_method else "├─"} 🔹 {modifiers} {return_type} {method.name}({params})'
                        '</div>'
                    )

                    method_vars, loops = _process_method_body(method.body)

                    if method_vars:
                        output.append(f'<div class="ast-subsection">{method_indent}    {method_prefix} │ └─ 🟡 Variables:')
                        for var in method_vars:
                            output.append(f'<div class="ast-var">{method_indent}    {method_prefix} │     ├─ {var}</div>')
                        output.append('</div>')

                    if loops:
                        output.append(f'<div class="ast-subsection">{method_indent}    {method_prefix} └─ 🔁 Loops:')
                        for loop in loops:
                            output.append(f'<div class="ast-loop">{method_indent}    {method_prefix}       ├─ {loop["type"]} Loop')
                            if loop['vars']:
                                for var in loop['vars']:
                                    output.append(f'<div class="ast-loop-var">{method_indent}    {method_prefix}       │   ├─ 🟠 {var}</div>')
                            else:
                                output.append(f'<div class="ast-loop-empty">{method_indent}    {method_prefix}       │   └─ (no variables)</div>')
                        output.append('</div>')

                output.append('</div>')
            
            # Render child classes (subclasses)
            if class_name in inheritance_map:
                child_indent = indent + ("    " if indent_level > 0 else "")
                output.append(f'<div class="ast-subsection">{child_indent}└─ 🔗 Subclasses:')
                for child_class in inheritance_map[class_name]:
                    render_class_recursive(child_class, indent_level + 1)
                output.append('</div>')
        
        # Render all root classes (those without parents in our code)
        for root_class in root_classes:
            render_class_recursive(root_class, 0)

        output.append('</div>')
        return '\n'.join(output)

    except javalang.parser.JavaSyntaxError as e:
        line_number = 'unknown'
        if e.at:
            if isinstance(e.at, javalang.tokenizer.Position):
                line_number = e.at.line
            elif hasattr(e.at, 'position'):
                line_number = e.at.position.line
        return f'<div class="ast-error">Java Syntax Error (Line {line_number}): {e.description}</div>'


def _process_method_body(body): #
    # ... (your _process_method_body function)
    method_vars = []
    loops = []

    if not body:
        return method_vars, loops

    if isinstance(body, javalang.tree.BlockStatement):
        statements = body.statements
    else:
        statements = [body] if body else []

    def _collect_loop_vars(loop_node):
        loop_vars = []
        if isinstance(loop_node, javalang.tree.ForStatement):
            if loop_node.control and loop_node.control.init:
                for init in loop_node.control.init:
                    if isinstance(init, javalang.tree.VariableDeclaration):
                        loop_vars.extend([f"{init.type.name} {d.name}" for d in init.declarators])

        if loop_node.body:
            body_statements = loop_node.body.statements if isinstance(loop_node.body, javalang.tree.BlockStatement) else [loop_node.body]
            for stmt in body_statements:
                if isinstance(stmt, javalang.tree.LocalVariableDeclaration):
                    loop_vars.extend([f"{stmt.type.name} {d.name}" for d in stmt.declarators])
        return loop_vars

    if body: # This condition might be redundant due to the initial check
        for stmt in statements: # Use 'statements' which is guaranteed to be a list
            if isinstance(stmt, javalang.tree.LocalVariableDeclaration):
                method_vars.extend([f"{stmt.type.name} {d.name}" for d in stmt.declarators])

            if isinstance(stmt, (javalang.tree.ForStatement,
                                  javalang.tree.WhileStatement,
                                  javalang.tree.DoStatement)):
                loop_type = stmt.__class__.__name__.replace("Statement", "")
                loops.append({
                    "type": loop_type,
                    "vars": _collect_loop_vars(stmt)
                })

    return method_vars, loops


def clean_comment(raw_comment: str) -> str: #
    sentences = [s.strip() for s in raw_comment.split('.') if s.strip()]
    filtered = []

    for sentence in sentences:
        filtered.append(sentence[0].upper() + sentence[1:])

    return '. '.join(filtered) + '.' if filtered else "No comment generated"


def extract_methods(java_code: str) -> dict: #
    # Remember to return jsonify errors or raise custom exceptions to be handled by routes
    try:
        # Wrap code in class if needed
        wrapped_code, was_wrapped = wrap_code_if_needed(java_code)
        tree = javalang.parse.parse(wrapped_code)
        lines = java_code.splitlines()
        method_map = {}
        
        # Adjust line offset if code was wrapped (wrapped code adds 1 line at the start)
        line_offset = 1 if was_wrapped else 0

        for _, class_node in tree.filter(javalang.tree.ClassDeclaration):
            class_name = class_node.name
            method_map[class_name] = []

            for method in class_node.methods:
                if method.body is None:
                    continue

                # Adjust line number if code was wrapped
                start_line = (method.position.line - 1 - line_offset) if method.position else 0
                start_line = max(0, start_line)  # Ensure non-negative

                brace_count = 0
                method_lines = []
                in_method_body = False

                for i in range(start_line, len(lines)):
                    line = lines[i]

                    if '{' in line and not in_method_body:
                        in_method_body = True
                        brace_count += line.count('{')
                        method_lines.append(line)
                        continue

                    if in_method_body:
                        method_lines.append(line)
                        brace_count += line.count('{')
                        brace_count -= line.count('}')

                        if brace_count == 0:
                            break

                method_code = '\n'.join(method_lines).strip()

                if not method_code or '{' not in method_code:
                    continue

                method_map[class_name].append({
                    'name': method.name,
                    'code': method_code
                })
        return method_map
    except javalang.parser.JavaSyntaxError as e:
        # Consider raising an error instead of returning jsonify here,
        # so the route can handle the HTTP response.
        # For now, returning a dict that the route can jsonify.
        line_number = 'unknown'
        if e.at:
            if isinstance(e.at, javalang.tokenizer.Position): line_number = e.at.line
            elif hasattr(e.at, 'position'): line_number = e.at.position.line
        return {'error': f'Java Syntax Error (Line {line_number}): {e.description}'}


def extract_classes(java_code: str) -> dict: #
    # ... (your extract_classes function)
    try:
        # Wrap code in class if needed
        wrapped_code, was_wrapped = wrap_code_if_needed(java_code)
        tree = javalang.parse.parse(wrapped_code)
        lines = java_code.splitlines()
        class_map = {}
        
        # Adjust line offset if code was wrapped (wrapped code adds 1 line at the start)
        line_offset = 1 if was_wrapped else 0

        for _, class_node in tree.filter(javalang.tree.ClassDeclaration):
            class_name = class_node.name
            # Adjust line number if code was wrapped
            start_line = (class_node.position.line - 1 - line_offset) if class_node.position else 0
            start_line = max(0, start_line)  # Ensure non-negative

            brace_count = 0
            class_lines = []
            in_class = False

            for i in range(start_line, len(lines)):
                line = lines[i]
                class_lines.append(line.strip())

                brace_count += line.count('{')
                brace_count -= line.count('}')

                if not in_class and '{' in line:
                    in_class = True
                    # Reset brace_count when first open brace of class is found.
                    # This assumes classes are not nested in a way that confuses this simple counter.
                    brace_count = line.count('{') - line.count('}')
                elif in_class and brace_count <= 0: # <= 0 to handle case where open and close are on same line
                    # If we started with a brace, we need to find its match.
                    # If the first line had more '{' than '}', this logic might need adjustment.
                    # A more robust way is to count from the class declaration line's first '{'.
                    break

            class_code = ' '.join(class_lines).strip()
            class_map[class_name] = class_code
        return class_map
    except javalang.parser.JavaSyntaxError as e:
        line_number = 'unknown'
        if e.at:
            if isinstance(e.at, javalang.tokenizer.Position): line_number = e.at.line
            elif hasattr(e.at, 'position'): line_number = e.at.position.line
        return {'error': f'Java Syntax Error (Line {line_number}): {e.description}'}


def compute_hash(code): #
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


def detect_relationships(java_code: str) -> dict:
    """
    Detect association, aggregation, and composition relationships between classes.
    
    Returns a dictionary with structure:
    {
        'association': [{'from': 'ClassA', 'to': 'ClassB', 'via': 'field/method', 'details': '...'}],
        'aggregation': [...],
        'composition': [...]
    }
    """
    relationships = {
        'association': [],
        'aggregation': [],
        'composition': []
    }
    
    try:
        wrapped_code, was_wrapped = wrap_code_if_needed(java_code)
        tree = javalang.parse.parse(wrapped_code)
        
        # Get all class names in the code
        class_names = set()
        class_nodes_map = {}
        
        for _, class_node in tree.filter(javalang.tree.ClassDeclaration):
            class_names.add(class_node.name)
            class_nodes_map[class_node.name] = class_node
        
        # Analyze each class for relationships
        for class_name, class_node in class_nodes_map.items():
            # Check fields (association/aggregation/composition)
            if class_node.fields:
                for field in class_node.fields:
                    field_type_name = None
                    generic_arg_name = None
                    
                    if field.type:
                        # Get base type name
                        if hasattr(field.type, 'name'):
                            field_type_name = field.type.name
                        
                        # Check for generic type arguments (e.g., List<Employee>)
                        if hasattr(field.type, 'arguments') and field.type.arguments:
                            for arg in field.type.arguments:
                                if hasattr(arg, 'name') and arg.name in class_names:
                                    generic_arg_name = arg.name
                                    # This is a collection/array relationship (aggregation)
                                    relationships['aggregation'].append({
                                        'from': class_name,
                                        'to': arg.name,
                                        'via': f'field: {field_type_name or "Collection"}<{arg.name}>',
                                        'details': f'Field: {[d.name for d in field.declarators]}'
                                    })
                    
                    # Check if base type is a class in our code (skip if we already handled it as generic)
                    if field_type_name and field_type_name in class_names and field_type_name != generic_arg_name:
                        # Determine relationship type based on field characteristics
                        # Check if it's a collection/array (aggregation)
                        is_collection = False
                        if hasattr(field.type, 'name'):
                            type_name = field.type.name.lower()
                            is_collection = any(coll in type_name for coll in ['list', 'arraylist', 'set', 'hashset', 'collection', 'map', 'hashmap'])
                        
                        if is_collection:
                            rel_type = 'aggregation'
                        else:
                            # Check modifiers to determine composition vs association
                            # Composition: typically final, private, and initialized in constructor
                            # Association: typically not final, or public/protected
                            is_final = field.modifiers and 'final' in field.modifiers
                            is_private = field.modifiers and 'private' in field.modifiers
                            
                            # Check if field is initialized in constructor (composition indicator)
                            initialized_in_constructor = False
                            if class_node.methods:
                                for method in class_node.methods:
                                    # Check if this is a constructor
                                    is_constructor = (method.name == class_node.name) or (hasattr(method, 'name') and method.name == '<init>')
                                    if is_constructor and method.body:
                                        body_str = str(method.body)
                                        for declarator in field.declarators:
                                            if declarator.name in body_str and 'new ' in body_str:
                                                initialized_in_constructor = True
                                                break
                            
                            if is_final and is_private and initialized_in_constructor:
                                rel_type = 'composition'
                            else:
                                rel_type = 'association'
                        
                        relationships[rel_type].append({
                            'from': class_name,
                            'to': field_type_name,
                            'via': 'field',
                            'details': f'Field: {[d.name for d in field.declarators]}'
                        })
            
            # Check method parameters (association)
            if class_node.methods:
                for method in class_node.methods:
                    if method.parameters:
                        for param in method.parameters:
                            param_type_name = None
                            if param.type:
                                if hasattr(param.type, 'name'):
                                    param_type_name = param.type.name
                            
                            if param_type_name and param_type_name in class_names:
                                relationships['association'].append({
                                    'from': class_name,
                                    'to': param_type_name,
                                    'via': 'method parameter',
                                    'details': f'Method: {method.name}(...)'
                                })
            
            # Check method return types (association)
            if class_node.methods:
                for method in class_node.methods:
                    if method.return_type:
                        return_type_name = None
                        if hasattr(method.return_type, 'name'):
                            return_type_name = method.return_type.name
                        
                        if return_type_name and return_type_name in class_names:
                            relationships['association'].append({
                                'from': class_name,
                                'to': return_type_name,
                                'via': 'method return type',
                                'details': f'Method: {method.name}()'
                            })
        
        # Remove duplicates
        for rel_type in relationships:
            seen = set()
            unique_rels = []
            for rel in relationships[rel_type]:
                key = (rel['from'], rel['to'], rel['via'])
                if key not in seen:
                    seen.add(key)
                    unique_rels.append(rel)
            relationships[rel_type] = unique_rels
        
        return relationships
    
    except Exception as e:
        # Return empty relationships on error
        return {'association': [], 'aggregation': [], 'composition': []}


# utils.py
def build_ast_json(java_code: str) -> dict:
    try:
        # Wrap code in class if needed
        wrapped_code, was_wrapped = wrap_code_if_needed(java_code)
        tree = javalang.parse.parse(wrapped_code)
        classes = []
        
        # Extract classes and methods first to generate comments
        class_structure = extract_classes(java_code)
        method_structure = extract_methods(java_code)
        
        # Get pipeline reference before processing
        hf_pipeline = current_app.hf_pipeline
        
        # Generate comments using batch processing for maximum speed
        class_comments = {}
        method_comments = {}
        
        if hf_pipeline:
            # Prepare all inputs for batch processing
            all_inputs = []
            input_mapping = []  # Track which input corresponds to which class/method
            
            # Add classes
            for class_name, class_code in class_structure.items():
                if isinstance(class_code, str):
                    processed_class = preprocess_code(class_code)
                    all_inputs.append(processed_class)
                    input_mapping.append(('class', class_name, None))
            
            # Add methods
            for class_name, methods in method_structure.items():
                if isinstance(methods, list):
                    for method in methods:
                        processed_method = preprocess_code(method['code'])
                        all_inputs.append(processed_method)
                        input_mapping.append(('method', class_name, method['name']))
            
            # Process in batches (model can handle multiple inputs at once)
            if all_inputs:
                try:
                    # Process all inputs in one batch call (much faster than individual calls)
                    batch_results = hf_pipeline(all_inputs, batch_size=min(8, len(all_inputs)))
                    
                    # Map results back to classes/methods
                    for idx, (input_type, class_name, method_name) in enumerate(input_mapping):
                        if idx < len(batch_results):
                            result = batch_results[idx]
                            comment = clean_comment(result['generated_text'])
                            
                            if input_type == 'class':
                                class_comments[class_name] = comment
                            else:  # method
                                method_comments[(class_name, method_name)] = comment
                except Exception as e:
                    # Fallback to sequential if batch fails
                    print(f"Batch processing failed, falling back to sequential: {e}")
                    for class_name, class_code in class_structure.items():
                        if isinstance(class_code, str):
                            try:
                                processed_class = preprocess_code(class_code)
                                result = hf_pipeline(processed_class)
                                comment = clean_comment(result[0]['generated_text'])
                                class_comments[class_name] = comment
                            except Exception as e2:
                                print(f"Error generating AST comment for class {class_name}: {e2}")
                    
                    for class_name, methods in method_structure.items():
                        if isinstance(methods, list):
                            for method in methods:
                                try:
                                    processed_method = preprocess_code(method['code'])
                                    result = hf_pipeline(processed_method)
                                    comment = clean_comment(result[0]['generated_text'])
                                    method_comments[(class_name, method['name'])] = comment
                                except Exception as e2:
                                    print(f"Error generating AST comment for method {class_name}.{method['name']}: {e2}")

        # First pass: collect all classes and their inheritance relationships
        class_nodes_map = {}
        inheritance_map = {}  # Maps parent class name -> list of child class names
        child_to_parent = {}  # Maps child class name -> parent class name
        root_classes = []  # Classes that don't extend anything (or extend external classes)
        
        for _, class_node in tree.filter(javalang.tree.ClassDeclaration):
            class_name = class_node.name
            class_nodes_map[class_name] = class_node
            
            # Check if class extends another class
            if hasattr(class_node, 'extends') and class_node.extends:
                # Get the superclass name
                parent_name = None
                if hasattr(class_node.extends, 'name'):
                    parent_name = class_node.extends.name
                elif isinstance(class_node.extends, list) and len(class_node.extends) > 0:
                    parent_name = class_node.extends[0].name if hasattr(class_node.extends[0], 'name') else str(class_node.extends[0])
                else:
                    parent_name = str(class_node.extends)
                
                # Check if parent class exists in our code
                if parent_name and parent_name in class_nodes_map:
                    # Parent is in our code, add to inheritance map
                    if parent_name not in inheritance_map:
                        inheritance_map[parent_name] = []
                    inheritance_map[parent_name].append(class_name)
                    child_to_parent[class_name] = parent_name
                else:
                    # Parent is external, treat as root class
                    root_classes.append(class_name)
            else:
                # No extends, this is a root class
                root_classes.append(class_name)
        
        # Helper function to build class data recursively
        def build_class_data(class_name):
            if class_name not in class_nodes_map:
                return None
            
            class_node = class_nodes_map[class_name]
            
            # Show inheritance info in name
            extends_info = ""
            if hasattr(class_node, 'extends') and class_node.extends:
                if hasattr(class_node.extends, 'name'):
                    parent_name = class_node.extends.name
                elif isinstance(class_node.extends, list) and len(class_node.extends) > 0:
                    parent_name = class_node.extends[0].name if hasattr(class_node.extends[0], 'name') else str(class_node.extends[0])
                else:
                    parent_name = str(class_node.extends)
                extends_info = f" extends {parent_name}"
            
            class_data = {
                "name": f"{class_name}{extends_info}",
                "type": "class",
                "comment": class_comments.get(class_name, "No comment available"),
                "children": []
            }

            # Fields
            if class_node.fields:
                fields_node = {
                    "name": "Fields",
                    "type": "fields",
                    "children": []
                }
                for field in class_node.fields:
                    modifiers = " ".join(field.modifiers) if field.modifiers else ""
                    field_type = field.type.name if field.type else "Unknown"
                    for declarator in field.declarators:
                        field_data = {
                            "name": f"{modifiers} {field_type} {declarator.name}",
                            "type": "field"
                        }
                        fields_node["children"].append(field_data)
                class_data["children"].append(fields_node)

            # Methods
            if class_node.methods:
                methods_node = {
                    "name": "Methods",
                    "type": "methods",
                    "children": []
                }
                for method in class_node.methods:
                    modifiers = " ".join(method.modifiers) if method.modifiers else ""
                    return_type = method.return_type.name if method.return_type else "void"
                    params = ", ".join([f"{p.type.name} {p.name}" for p in method.parameters]) if method.parameters else ""
                    method_data = {
                        "name": f"{modifiers} {return_type} {method.name}({params})",
                        "type": "method",
                        "comment": method_comments.get((class_name, method.name), "No comment available")
                    }
                    methods_node["children"].append(method_data)
                class_data["children"].append(methods_node)
            
            # Add child classes (subclasses) as children
            if class_name in inheritance_map:
                subclasses_node = {
                    "name": "Subclasses",
                    "type": "subclasses",
                    "children": []
                }
                for child_class_name in inheritance_map[class_name]:
                    child_class_data = build_class_data(child_class_name)
                    if child_class_data:
                        subclasses_node["children"].append(child_class_data)
                if subclasses_node["children"]:
                    class_data["children"].append(subclasses_node)
            
            return class_data
        
        # Build AST starting from root classes
        classes = []
        for root_class in root_classes:
            class_data = build_class_data(root_class)
            if class_data:
                classes.append(class_data)
        
        return {"name": "Root", "type": "root", "children": classes}
    
    except javalang.parser.JavaSyntaxError as e:
        return {"error": f"Java Syntax Error: {e.description}"}