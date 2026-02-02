# app/cfg_utils.py
import javalang
import networkx as nx
from graphviz import Digraph
import os
import re

class CFGGenerator:
    def __init__(self):
        self.cfg = nx.DiGraph()
        self.current_block = None
        self.block_counter = 0
        self.break_targets = []
        self.continue_targets = []
        self.line_map = {}  # Map statements to line numbers
        self.java_code = ""  # Store original code
        self.method_map = {}  # Map method names to method nodes
        self.method_entries = {}  # Map method names to their entry blocks
        self.method_exits = {}  # Map method names to their exit blocks
        self.method_colors = {}  # Map method names to their unique colors
        self.node_method_map = {}  # Map node IDs to method names for coloring
        self.call_stack = []  # Track method call stack: [(method_name, block_id), ...]
        self.in_infinite_loop = False  # Track if we're in an infinite loop context

    def generate(self, java_code: str) -> nx.DiGraph:
        """Generate CFG from Java code"""
        self.java_code = java_code
        try:
            # Try to parse as-is first
            tree = javalang.parse.parse(java_code)
            self._build_line_map(java_code)
            self._process_tree(tree)
            return self.cfg
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
                "expected" in error_desc and "declaration" in error_desc
            )
            
            # If error is at line 1 and is about type declaration, wrap in class
            if error_line == 1 and is_type_declaration_error:
                try:
                    # Wrap code in a public class
                    wrapped_code = f"public class nan {{\n{java_code}\n}}"
                    tree = javalang.parse.parse(wrapped_code)
                    self._build_line_map(java_code)  # Use original for line mapping
                    self._process_tree(tree)
                    return self.cfg
                except Exception as wrap_error:
                    # If wrapping also fails, raise original error
                    raise ValueError(f"Java syntax error: {e}")
            
            # If parsing fails for other reasons, try wrapping in a class if it doesn't start with class
            try:
                stripped = java_code.strip()
                if not stripped.startswith('class ') and not stripped.startswith('public class ') and \
                   not stripped.startswith('private class ') and not stripped.startswith('protected class '):
                    # Try wrapping in a dummy class
                    wrapped_code = f"public class nan {{\n{java_code}\n}}"
                    tree = javalang.parse.parse(wrapped_code)
                    self._build_line_map(java_code)  # Use original for line mapping
                    self._process_tree(tree)
                    return self.cfg
            except:
                pass
            
            raise ValueError(f"Java syntax error: {e}")

    def _build_line_map(self, java_code):
        """Map statements to line numbers"""
        lines = java_code.splitlines()
        for i, line in enumerate(lines):
            self.line_map[i+1] = line.strip()

    def _process_tree(self, tree):
        """Process AST to build CFG"""
        # First pass: collect all method declarations
        current_class = None
        method_list = []
        for path, node in tree:
            if isinstance(node, javalang.tree.ClassDeclaration):
                current_class = node.name
            elif isinstance(node, javalang.tree.MethodDeclaration):
                # Store method by class and name
                method_key = f"{current_class}.{node.name}" if current_class else node.name
                self.method_map[method_key] = node
                self.method_map[node.name] = node  # Also store by name only for easier lookup
                method_list.append((node.name, node))
        
        # Assign unique colors to each method
        color_palette = [
            '#FFE5B4',  # Peach
            '#E6E6FA',  # Lavender
            '#B4E6FF',  # Light blue
            '#FFB4E6',  # Light pink
            '#B4FFE6',  # Mint green
            '#FFFFB4',  # Light yellow
            '#E6B4FF',  # Light purple
            '#B4FFB4',  # Light green
            '#FFE6B4',  # Light orange
            '#B4E6E6',  # Light cyan
            '#FFB4B4',  # Light red
            '#B4B4FF',  # Light indigo
            '#FFD4B4',  # Light apricot
            '#D4FFB4',  # Light lime
            '#B4FFD4',  # Light aquamarine
        ]
        for idx, (method_name, method_node) in enumerate(method_list):
            self.method_colors[method_name] = color_palette[idx % len(color_palette)]
        
        # Second pass: process methods
        for path, node in tree:
            if isinstance(node, javalang.tree.MethodDeclaration):
                self._process_method(node)

    def _process_method(self, method_node):
        """Process a method's CFG"""
        start_line = method_node.position.line if method_node.position else "?"
        method_key = method_node.name
        
        # Check if method entry already exists (method was already processed)
        if method_key in self.method_entries:
            return
        
        # Reset infinite loop flag for each new method
        self.in_infinite_loop = False
        
        # Push this method onto the call stack BEFORE creating entry block
        # This ensures the entry block gets this method's color
        self.call_stack.append((method_key, None))
        
        method_entry = self._new_block(f"METHOD ENTRY: {method_node.name}\nLine: {start_line}")
        self.current_block = method_entry
        
        # Store method entry and assign color
        self.method_entries[method_key] = method_entry
        self.node_method_map[method_entry] = method_key
        # Update stack with actual entry block
        self.call_stack[-1] = (method_key, method_entry)

        if method_node.body:
            self._process_block(method_node.body)
            # If method doesn't end with return, create implicit exit
            # Check if last block is already a method exit
            exit_blocks = []
            if self.current_block and "METHOD EXIT" not in self.cfg.nodes[self.current_block].get("label", ""):
                # Check if there's already an exit edge
                has_exit = False
                for _, dst in self.cfg.out_edges(self.current_block):
                    if "METHOD EXIT" in self.cfg.nodes[dst].get("label", ""):
                        has_exit = True
                        exit_blocks.append(dst)
                        break
                if not has_exit:
                    exit_block = self._new_block("METHOD EXIT")
                    self._connect_blocks(self.current_block, exit_block)
                    exit_blocks.append(exit_block)
                    self.node_method_map[exit_block] = method_key
            else:
                # Find all exit blocks
                for node in self.cfg.nodes():
                    if "METHOD EXIT" in self.cfg.nodes[node].get("label", "") and \
                       self._is_reachable_from(method_entry, node):
                        exit_blocks.append(node)
                        if node not in self.node_method_map:
                            self.node_method_map[node] = method_key
            
            # Store method exits
            if exit_blocks:
                self.method_exits[method_key] = exit_blocks
            else:
                # If no exit found, create one
                exit_block = self._new_block("METHOD EXIT")
                if self.current_block:
                    self._connect_blocks(self.current_block, exit_block)
                self.method_exits[method_key] = [exit_block]
                self.node_method_map[exit_block] = method_key
        
        # Pop this method from the call stack when done processing
        if self.call_stack and self.call_stack[-1][0] == method_key:
            self.call_stack.pop()

    def _process_block(self, block_node):
        """Process a block of statements"""
        for stmt in block_node:
            # If we're in an infinite loop context, don't process further statements
            # (they're unreachable and shouldn't be connected to the loop)
            if self.in_infinite_loop:
                # Don't process or connect any statements after infinite loop
                # They are unreachable code
                break
            else:
                self._process_statement(stmt)

    def _process_statement(self, stmt):
        """Process individual statements"""
        if isinstance(stmt, javalang.tree.IfStatement):
            self._process_if_statement(stmt)
        elif isinstance(stmt, javalang.tree.WhileStatement):
            self._process_while_statement(stmt)
        elif isinstance(stmt, javalang.tree.ForStatement):
            self._process_for_statement(stmt)
        elif isinstance(stmt, javalang.tree.DoStatement):
            self._process_do_statement(stmt)
        elif isinstance(stmt, javalang.tree.SwitchStatement):
            self._process_switch_statement(stmt)
        elif isinstance(stmt, javalang.tree.BlockStatement):
            self._process_block(stmt.statements)
        elif isinstance(stmt, javalang.tree.ReturnStatement):
            self._add_statement_to_block(stmt)
            # Create end block for return
            end_block = self._new_block("METHOD EXIT")
            self._connect_blocks(self.current_block, end_block)
            self.current_block = end_block
        elif isinstance(stmt, javalang.tree.StatementExpression):
            # Check if this is a method call
            if isinstance(stmt.expression, javalang.tree.MethodInvocation):
                self._process_method_invocation(stmt.expression)
            else:
                self._add_statement_to_block(stmt)
        else:
            self._add_statement_to_block(stmt)

    def _add_statement_to_block(self, stmt):
        """Add statement to current block with line number"""
        line_no = stmt.position.line if stmt.position else "?"
        stmt_type = type(stmt).__name__.replace("Statement", "")
        
        # Get statement text from original code
        stmt_text = ""
        if stmt.position:
            stmt_text = self._get_statement_text(stmt.position.line)
        
        # Add to current block
        if "label" not in self.cfg.nodes[self.current_block]:
            self.cfg.nodes[self.current_block]['label'] = ""
        self.cfg.nodes[self.current_block]['label'] += f"\nL{line_no}: {stmt_text}"

    def _get_statement_text(self, line_no):
        """Get original statement text from line number"""
        if line_no in self.line_map:
            return self.line_map[line_no][:100]  # Truncate long lines
        return ""
    
    def _extract_condition_text(self, condition_node):
        """Extract readable condition text from condition node - returns only the condition expression"""
        if condition_node is None:
            return "true"
        
        # First try to reconstruct from AST (more reliable and avoids duplication)
        if isinstance(condition_node, javalang.tree.Literal):
            return str(condition_node.value)
        elif isinstance(condition_node, javalang.tree.MemberReference):
            return condition_node.member
        elif isinstance(condition_node, javalang.tree.BinaryOperation):
            left = self._extract_condition_text(condition_node.operandl) if hasattr(condition_node, 'operandl') else "?"
            right = self._extract_condition_text(condition_node.operandr) if hasattr(condition_node, 'operandr') else "?"
            op = condition_node.operator if hasattr(condition_node, 'operator') else "?"
            return f"{left} {op} {right}"
        elif isinstance(condition_node, javalang.tree.MethodInvocation):
            method_name = condition_node.member if hasattr(condition_node, 'member') else "?"
            args = ""
            if hasattr(condition_node, 'arguments') and condition_node.arguments:
                # Try to get argument count or simple representation
                args = f"({len(condition_node.arguments)} args)"
            return f"{method_name}{args}"
        elif hasattr(javalang.tree, 'UnaryExpression') and isinstance(condition_node, javalang.tree.UnaryExpression):
            # Handle unary expressions like !x, -x
            if hasattr(condition_node, 'operator') and hasattr(condition_node, 'expression'):
                op = condition_node.operator
                expr = self._extract_condition_text(condition_node.expression)
                return f"{op}{expr}"
        
        # Fallback: try to get from line number and extract condition part
        # Only use this if AST reconstruction didn't work
        if condition_node.position:
            line_text = self._get_statement_text(condition_node.position.line)
            if line_text:
                # Try to extract just the condition part (remove while/for/if keywords)
                # Remove common patterns like "while (", "for (", "if ("
                cond_text = re.sub(r'^\s*(while|for|if|do)\s*\(', '', line_text, flags=re.IGNORECASE)
                cond_text = re.sub(r'\)\s*\{?\s*$', '', cond_text)
                cond_text = cond_text.strip()
                # Also try to remove any leading/trailing whitespace and braces
                cond_text = re.sub(r'^\s*\(?\s*', '', cond_text)
                cond_text = re.sub(r'\s*\)?\s*$', '', cond_text)
                # Clean up: remove any line number patterns like "L123:" that might be in the text
                cond_text = re.sub(r'L\d+:\s*', '', cond_text)
                # Remove any duplicate words (simple deduplication)
                words = cond_text.split()
                seen = set()
                unique_words = []
                for word in words:
                    if word not in seen:
                        seen.add(word)
                        unique_words.append(word)
                cond_text = ' '.join(unique_words)
                if cond_text:
                    # Limit to first 80 chars
                    return cond_text[:80]
        
        return "condition"

    def _process_if_statement(self, if_node):
        """Process if statement"""
        cond_line = if_node.condition.position.line if if_node.condition.position else "?"
        cond_text = self._get_statement_text(cond_line)
        cond_block = self._new_block(f"IF CONDITION\nL{cond_line}: {cond_text}")
        
        # Connect current block to condition
        self._connect_blocks(self.current_block, cond_block)
        
        # Process then branch
        then_block = self._new_block("THEN BRANCH")
        self._connect_blocks(cond_block, then_block)
        prev_block = self.current_block
        self.current_block = then_block
        self._process_statement(if_node.then_statement)
        
        # Create merge point
        merge_block = self._new_block("IF MERGE")
        self._connect_blocks(then_block, merge_block)
        
        # Process else branch if exists
        if if_node.else_statement:
            else_block = self._new_block("ELSE BRANCH")
            self._connect_blocks(cond_block, else_block)
            self.current_block = else_block
            self._process_statement(if_node.else_statement)
            self._connect_blocks(else_block, merge_block)
        else:
            # Connect condition directly to merge block
            self._connect_blocks(cond_block, merge_block)
        
        self.current_block = merge_block

    def _process_while_statement(self, while_node):
        """Process while loop"""
        cond_line = while_node.condition.position.line if while_node.condition.position else "?"
        cond_text = self._extract_condition_text(while_node.condition)
        
        # Check if loop never runs (always false condition)
        never_runs = self._is_always_false_condition(while_node.condition)
        
        if never_runs:
            # Loop never runs - create nodes but don't connect them with arrows
            line_label = f"L{cond_line}: " if cond_line != "?" else ""
            cond_block = self._new_block(f"WHILE CONDITION\n{line_label}{cond_text}")
            body_block = self._new_block("LOOP BODY")
            
            # Process body to create its nodes (but don't connect)
            saved_block = self.current_block
            self.current_block = body_block
            self._process_statement(while_node.body)
            self.current_block = saved_block  # Restore - don't connect loop nodes
            
            # Create exit block but don't connect from condition
            exit_block = self._new_block("LOOP EXIT")
            # Connect from previous block to exit (skip the loop entirely)
            self._connect_blocks(self.current_block, exit_block)
            self.current_block = exit_block
            return
        
        # Analyze loop termination using condition and body analysis
        is_infinite, reason = self._analyze_loop_termination(while_node.condition, while_node.body)
        
        # Fallback to simple check if analysis didn't find variables
        if not is_infinite:
            is_infinite = self._is_infinite_loop_condition(while_node.condition)
        
        line_label = f"L{cond_line}: " if cond_line != "?" else ""
        cond_block = self._new_block(f"WHILE CONDITION\n{line_label}{cond_text}")
        
        # Connect current block to condition
        self._connect_blocks(self.current_block, cond_block)
        
        # Create loop body block
        body_block = self._new_block("LOOP BODY")
        # Always connect condition to body (true branch)
        self._connect_blocks(cond_block, body_block)
        
        # Process body
        self.current_block = body_block
        self._process_statement(while_node.body)
        self._connect_blocks(body_block, cond_block)  # Loop back
        
        # Handle exit block based on whether loop is infinite
        if not is_infinite:
            # Normal loop: condition can go to body or exit
            exit_block = self._new_block("LOOP EXIT")
            self._connect_blocks(cond_block, exit_block)
            self.current_block = exit_block
        else:
            # For infinite loops, don't create exit node and don't allow further connections
            # Mark that we're in an infinite loop context - no exit path exists
            self.in_infinite_loop = True
            # Set current_block to cond_block but mark it so no further connections are made
            # The loop only has: previous -> condition -> body -> condition (loop back)
            # No arrow from condition to any exit or subsequent node
            self.current_block = cond_block

    def _process_for_statement(self, for_node):
        """Process for loop"""
        # Create init block
        init_block = self._new_block("FOR INIT")
        self._connect_blocks(self.current_block, init_block)
        
        # Handle different for loop types
        is_foreach = hasattr(for_node, 'control') and isinstance(for_node.control, javalang.tree.EnhancedForControl)
        has_condition = hasattr(for_node, 'control') and hasattr(for_node.control, 'condition') and for_node.control.condition is not None
        
        # Condition block - handle all cases
        cond_line = "?"
        cond_text = "true"
        
        if is_foreach:
            # For-each loop (enhanced for loop)
            cond_line = for_node.position.line if for_node.position else "?"
            var_name = for_node.control.var.name if hasattr(for_node.control.var, 'name') else "?"
            
            # Extract iterable name - handle different types (MemberReference, MethodInvocation, etc.)
            iterable = "?"
            if hasattr(for_node.control, 'iterable') and for_node.control.iterable:
                iterable_node = for_node.control.iterable
                if isinstance(iterable_node, javalang.tree.MemberReference):
                    iterable = iterable_node.member
                elif isinstance(iterable_node, javalang.tree.MethodInvocation):
                    iterable = f"{iterable_node.member}()"
                elif hasattr(iterable_node, 'name'):
                    iterable = iterable_node.name
                else:
                    # Try to get a string representation
                    iterable = str(iterable_node)
            
            cond_text = f"for ({var_name} : {iterable})"
        elif has_condition:
            # Standard for loop with condition
            cond_line = for_node.control.condition.position.line if for_node.control.condition.position else "?"
            cond_text = self._extract_condition_text(for_node.control.condition)
        else:
            # Infinite loop (no condition)
            cond_line = for_node.position.line if for_node.position else "?"
            cond_text = "true"
        
        line_label = f"L{cond_line}: " if cond_line != "?" else ""
        cond_block = self._new_block(f"FOR CONDITION\n{line_label}{cond_text}")
        self._connect_blocks(init_block, cond_block)
        
        # Check if loop never runs (always false condition)
        never_runs = False
        if has_condition:
            never_runs = self._is_always_false_condition(for_node.control.condition)
        
        if never_runs:
            # Loop never runs - create nodes but don't connect them with arrows
            body_block = self._new_block("LOOP BODY")
            
            # Process body to create its nodes (but don't connect)
            saved_block = self.current_block
            self.current_block = body_block
            self._process_statement(for_node.body)
            self.current_block = saved_block  # Restore - don't connect loop nodes
            
            # Create exit block but don't connect from condition
            exit_block = self._new_block("LOOP EXIT")
            # Connect from init block to exit (skip the loop entirely)
            self._connect_blocks(init_block, exit_block)
            self.current_block = exit_block
            return
        
        # Create body block
        body_block = self._new_block("LOOP BODY")
        self._connect_blocks(cond_block, body_block)
        
        # Process body
        self.current_block = body_block
        self._process_statement(for_node.body)
        
        # Update block (if exists) - not present in for-each loops
        if not is_foreach and hasattr(for_node.control, 'update') and for_node.control.update:
            update_block = self._new_block("FOR UPDATE")
            self._connect_blocks(body_block, update_block)
            self.current_block = update_block
            # Add update statements
            for update_stmt in for_node.control.update:
                self._add_statement_to_block(update_stmt)
            self._connect_blocks(update_block, cond_block)
        else:
            self._connect_blocks(body_block, cond_block)
        
        # Analyze loop termination for for loops
        is_infinite = False
        if is_foreach:
            # Enhanced for loops (for-each) are always finite - they iterate over a collection/array
            is_infinite = False
        elif not has_condition:
            # No condition means infinite loop
            is_infinite = True
        elif has_condition:
            # For for loops, the update clause is critical - check it first
            # Analyze if condition variables are modified in a way that could terminate
            is_infinite, reason = self._analyze_loop_termination(for_node.control.condition, for_node.body)
            # Also check update statements - analyze modification direction in update clause
            # For for loops, update clause is the primary place where condition variables are modified
            if hasattr(for_node.control, 'update') and for_node.control.update:
                condition_vars = self._extract_variables_from_expression(for_node.control.condition)
                update_modification_directions = {}
                # Analyze modification direction in update statements
                for update_stmt in for_node.control.update:
                    # Update statements in for loops can be MemberReference directly (e.g., i++, i--)
                    # or StatementExpression. Handle both cases.
                    if isinstance(update_stmt, javalang.tree.MemberReference):
                        # Direct MemberReference with postfix/prefix operators
                        var_name = update_stmt.member
                        if hasattr(update_stmt, 'postfix_operators') and update_stmt.postfix_operators:
                            if '++' in update_stmt.postfix_operators:
                                update_modification_directions[var_name] = "increment"
                            elif '--' in update_stmt.postfix_operators:
                                update_modification_directions[var_name] = "decrement"
                        elif hasattr(update_stmt, 'prefix_operators') and update_stmt.prefix_operators:
                            if '++' in update_stmt.prefix_operators:
                                update_modification_directions[var_name] = "increment"
                            elif '--' in update_stmt.prefix_operators:
                                update_modification_directions[var_name] = "decrement"
                    else:
                        # StatementExpression or other types - need to wrap in StatementExpression for analysis
                        # Create a temporary StatementExpression wrapper if needed
                        if not isinstance(update_stmt, javalang.tree.StatementExpression):
                            # For other types, try to analyze directly
                            if isinstance(update_stmt, javalang.tree.Assignment):
                                # Handle assignment in update clause
                                if isinstance(update_stmt.expressionl, javalang.tree.MemberReference):
                                    var_name = update_stmt.expressionl.member
                                    # Check if it's a compound assignment
                                    if hasattr(update_stmt, 'operator'):
                                        if update_stmt.operator == "+=":
                                            update_modification_directions[var_name] = "increment"
                                        elif update_stmt.operator == "-=":
                                            update_modification_directions[var_name] = "decrement"
                        else:
                            self._analyze_modification_direction(update_stmt, update_modification_directions)
                    modified_vars = self._extract_modified_variables(update_stmt)
                    if condition_vars.intersection(modified_vars):
                        # Condition variable is modified in update - analyze direction
                        modified_var = list(condition_vars.intersection(modified_vars))[0]
                        mod_dir = update_modification_directions.get(modified_var, "unknown")
                        
                        # Analyze if modification direction leads to termination
                        if isinstance(for_node.control.condition, javalang.tree.BinaryOperation):
                            op = for_node.control.condition.operator
                            left = for_node.control.condition.operandl
                            right = for_node.control.condition.operandr
                            
                            # Check if left is variable and right is constant or member reference
                            if isinstance(left, javalang.tree.MemberReference):
                                if left.member == modified_var:
                                    # For > operator: variable > something
                                    # If variable is incremented, condition stays true (infinite)
                                    if op == ">" or op == ">=":
                                        if mod_dir == "increment":
                                            is_infinite = True
                                            break
                                        elif mod_dir == "decrement":
                                            is_infinite = False
                                            break
                                    # For < operator: variable < something
                                    # If variable is decremented, condition stays true (infinite)
                                    # If variable is incremented, condition can become false (terminate)
                                    if op == "<" or op == "<=":
                                        if mod_dir == "decrement":
                                            is_infinite = True
                                            break
                                        elif mod_dir == "increment":
                                            is_infinite = False
                                            break
                            
                            # Check if right is variable and left is constant or member reference
                            if isinstance(right, javalang.tree.MemberReference):
                                if right.member == modified_var:
                                    # For > operator: something > variable
                                    # If variable is decremented, condition stays true (infinite)
                                    if op == ">":
                                        if mod_dir == "decrement":
                                            is_infinite = True
                                            break
                                        elif mod_dir == "increment":
                                            is_infinite = False
                                            break
                                    # For < operator: something < variable
                                    # If variable is incremented, condition stays true (infinite)
                                    if op == "<":
                                        if mod_dir == "increment":
                                            is_infinite = True
                                            break
                                        elif mod_dir == "decrement":
                                            is_infinite = False
                                            break
                        else:
                            # If we can't analyze direction, assume it can terminate
                            is_infinite = False
                            break
                
                # If update clause didn't give us a definitive answer, check body
                if is_infinite is None:
                    is_infinite, reason = self._analyze_loop_termination(for_node.control.condition, for_node.body)
            else:
                # No update clause, analyze body
                is_infinite, reason = self._analyze_loop_termination(for_node.control.condition, for_node.body)
            
            # Fallback to simple check if still not determined
            if is_infinite is None:
                is_infinite = self._is_infinite_loop_condition(for_node.control.condition)
            elif is_infinite is False:
                # Double-check with simple condition check
                if self._is_infinite_loop_condition(for_node.control.condition):
                    is_infinite = True
        
        # Only create exit block if not infinite loop
        if not is_infinite:
            # Normal loop: condition can go to body or exit
            exit_block = self._new_block("LOOP EXIT")
            self._connect_blocks(cond_block, exit_block)
            self.current_block = exit_block
        else:
            # For infinite loops, don't create exit node and don't allow further connections
            # Mark that we're in an infinite loop context - no exit path exists
            self.in_infinite_loop = True
            # Set current_block to cond_block but mark it so no further connections are made
            # The loop only has: previous -> condition -> body -> condition (loop back)
            # No arrow from condition to any exit or subsequent node
            self.current_block = cond_block

    def _process_do_statement(self, do_node):
        """Process do-while loop"""
        cond_line = do_node.condition.position.line if do_node.condition.position else "?"
        cond_text = self._extract_condition_text(do_node.condition)
        
        # Check if loop never runs after first iteration (always false condition)
        never_runs = self._is_always_false_condition(do_node.condition)
        
        # Create body block first (do-while executes body before checking condition)
        body_block = self._new_block("DO-WHILE BODY")
        
        # Connect current block to body (do-while always executes body at least once)
        self._connect_blocks(self.current_block, body_block)
        
        if never_runs:
            # Loop never runs after first iteration - create nodes but don't loop back
            line_label = f"L{cond_line}: " if cond_line != "?" else ""
            cond_block = self._new_block(f"DO-WHILE CONDITION\n{line_label}{cond_text}")
            
            # Process body to create its nodes
            saved_block = self.current_block
            self.current_block = body_block
            self._process_statement(do_node.body)
            self.current_block = saved_block  # Restore
            
            # Connect body to condition (executes once)
            self._connect_blocks(body_block, cond_block)
            
            # Create exit block - connect from condition (loop executes once then exits)
            exit_block = self._new_block("LOOP EXIT")
            self._connect_blocks(cond_block, exit_block)
            self.current_block = exit_block
            return
        
        # Process body
        self.current_block = body_block
        self._process_statement(do_node.body)
        
        # Create condition block
        line_label = f"L{cond_line}: " if cond_line != "?" else ""
        cond_block = self._new_block(f"DO-WHILE CONDITION\n{line_label}{cond_text}")
        # Connect body to condition (always executed after body)
        self._connect_blocks(body_block, cond_block)
        
        # Analyze loop termination
        is_infinite, reason = self._analyze_loop_termination(do_node.condition, do_node.body)
        
        # Fallback to simple check if analysis didn't find variables
        if not is_infinite:
            is_infinite = self._is_infinite_loop_condition(do_node.condition)
        
        # Connect condition back to body (true branch - continue loop)
        self._connect_blocks(cond_block, body_block)
        
        # Handle exit block based on whether loop is infinite
        if not is_infinite:
            # Normal loop: condition can go to body or exit
            exit_block = self._new_block("LOOP EXIT")
            self._connect_blocks(cond_block, exit_block)
            self.current_block = exit_block
        else:
            # For infinite loops, don't create exit node and don't allow further connections
            # Mark that we're in an infinite loop context - no exit path exists
            self.in_infinite_loop = True
            # Set current_block to cond_block but mark it so no further connections are made
            self.current_block = cond_block

    def _process_switch_statement(self, switch_node):
        """Process switch statement"""
        expr_line = switch_node.expression.position.line if switch_node.expression.position else "?"
        expr_text = self._get_statement_text(expr_line)
        
        # Create switch expression block
        switch_block = self._new_block(f"SWITCH EXPRESSION\nL{expr_line}: {expr_text}")
        self._connect_blocks(self.current_block, switch_block)
        
        # Create a merge block for after switch
        merge_block = self._new_block("SWITCH MERGE")
        
        # Process each case
        case_blocks = {}
        case_statements_end_blocks = {}  # Track where each case ends
        
        if switch_node.cases:
            for i, case in enumerate(switch_node.cases):
                case_label = "default"
                case_conditions = []
                
                if case.case:
                    # This is a case with values
                    for case_value in case.case:
                        if isinstance(case_value, javalang.tree.Literal):
                            case_conditions.append(str(case_value.value))
                        elif isinstance(case_value, javalang.tree.MemberReference):
                            case_conditions.append(case_value.member)
                        else:
                            case_conditions.append(str(case_value))
                    case_label = "case " + ", ".join(case_conditions)
                else:
                    # This is the default case
                    case_label = "default"
                
                # Create case label block
                case_block = self._new_block(f"CASE: {case_label}")
                case_blocks[i] = case_block
                self._connect_blocks(switch_block, case_block)
                
                # Process case statements
                if case.statements:
                    self.current_block = case_block
                    has_break = False
                    
                    for stmt in case.statements:
                        # Check if this is a break statement
                        if isinstance(stmt, javalang.tree.BreakStatement):
                            # Break exits the switch - connect to merge block
                            break_block = self._new_block("BREAK")
                            self._connect_blocks(self.current_block, break_block)
                            self._connect_blocks(break_block, merge_block)
                            case_statements_end_blocks[i] = break_block
                            has_break = True
                            # Don't process further statements in this case after break
                            break
                        else:
                            self._process_statement(stmt)
                            case_statements_end_blocks[i] = self.current_block
                    
                    # Handle fall-through: if case doesn't end with break, connect to next case
                    if not has_break:
                        if i < len(switch_node.cases) - 1:
                            # Not the last case - falls through to next case
                            next_case_block = case_blocks.get(i + 1)
                            if next_case_block:
                                end_block = case_statements_end_blocks.get(i, case_block)
                                self._connect_blocks(end_block, next_case_block)
                        else:
                            # Last case - if no break, connect to merge
                            end_block = case_statements_end_blocks.get(i, case_block)
                            self._connect_blocks(end_block, merge_block)
                else:
                    # Empty case - falls through to next case or merge
                    case_statements_end_blocks[i] = case_block
                    if i < len(switch_node.cases) - 1:
                        # Falls through to next case
                        next_case_block = case_blocks.get(i + 1)
                        if next_case_block:
                            self._connect_blocks(case_block, next_case_block)
                    else:
                        # Last case - connect to merge
                        self._connect_blocks(case_block, merge_block)
        
        # Set current block to merge
        self.current_block = merge_block

    def _new_block(self, label=None):
        """Create a new basic block"""
        block_id = f"B{self.block_counter}"
        self.block_counter += 1
        self.cfg.add_node(block_id, label=label or "BLOCK")
        
        # Assign color based on current method in call stack
        if self.call_stack:
            current_method = self.call_stack[-1][0]
            self.node_method_map[block_id] = current_method
        else:
            # If no method in stack, try to find from context
            # This handles cases where blocks are created outside method context
            pass
        
        return block_id

    def _connect_blocks(self, from_block, to_block):
        """Connect two blocks in the CFG"""
        # Don't create edges if we're in an infinite loop context and trying to connect from the loop
        if self.in_infinite_loop and from_block != to_block:
            # Check if from_block is part of an infinite loop (has "WHILE CONDITION" or "FOR CONDITION" in label)
            from_label = self.cfg.nodes[from_block].get("label", "")
            if "WHILE CONDITION" in from_label or "FOR CONDITION" in from_label:
                # Don't create edge from infinite loop condition to anything outside the loop
                return
        self.cfg.add_edge(from_block, to_block)
    
    def _extract_variables_from_expression(self, expr):
        """Extract variable names from an expression"""
        variables = set()
        
        if isinstance(expr, javalang.tree.MemberReference):
            variables.add(expr.member)
        elif isinstance(expr, javalang.tree.BinaryOperation):
            variables.update(self._extract_variables_from_expression(expr.operandl))
            variables.update(self._extract_variables_from_expression(expr.operandr))
        elif hasattr(javalang.tree, 'UnaryExpression') and isinstance(expr, javalang.tree.UnaryExpression):
            # Handle unary expressions if they exist
            if hasattr(expr, 'operand'):
                variables.update(self._extract_variables_from_expression(expr.operand))
        elif isinstance(expr, javalang.tree.Cast):
            if expr.expression:
                variables.update(self._extract_variables_from_expression(expr.expression))
        elif isinstance(expr, javalang.tree.MethodInvocation):
            # Method calls might modify state, but we'll focus on direct variable access
            pass
        elif isinstance(expr, javalang.tree.Assignment):
            # Assignment expressions - extract from both sides
            if hasattr(expr, 'expressionl'):
                variables.update(self._extract_variables_from_expression(expr.expressionl))
            if hasattr(expr, 'value'):
                variables.update(self._extract_variables_from_expression(expr.value))
        
        return variables
    
    def _extract_modified_variables(self, stmt):
        """Extract variables that are modified in a statement"""
        modified = set()
        
        # Handle direct MemberReference (e.g., in for loop update clause: i++, i--)
        if isinstance(stmt, javalang.tree.MemberReference):
            # Check for postfix operators (a++, a--)
            if hasattr(stmt, 'postfix_operators') and stmt.postfix_operators:
                if stmt.member:
                    modified.add(stmt.member)
            # Check for prefix operators (++a, --a)
            elif hasattr(stmt, 'prefix_operators') and stmt.prefix_operators:
                if stmt.member:
                    modified.add(stmt.member)
        
        if isinstance(stmt, javalang.tree.StatementExpression):
            expr = stmt.expression
            if isinstance(expr, javalang.tree.Assignment):
                # Extract left-hand side variable
                if isinstance(expr.expressionl, javalang.tree.MemberReference):
                    modified.add(expr.expressionl.member)
                # Also check for compound assignments like +=, -=, etc.
                elif hasattr(expr.expressionl, 'member'):
                    modified.add(expr.expressionl.member)
            # Check for increment/decrement operations (postfix/prefix)
            # In javalang, postfix/prefix operations (i++, ++i, i--, --i) are represented
            # as MemberReference with postfix_operators or prefix_operators attributes
            elif isinstance(expr, javalang.tree.MemberReference):
                # Check for postfix operators (a++, a--)
                if hasattr(expr, 'postfix_operators') and expr.postfix_operators:
                    # postfix_operators is a list like ['++'] or ['--']
                    if expr.member:
                        modified.add(expr.member)
                # Check for prefix operators (++a, --a)
                elif hasattr(expr, 'prefix_operators') and expr.prefix_operators:
                    # prefix_operators is a list like ['++'] or ['--']
                    if expr.member:
                        modified.add(expr.member)
            # Check if expression has attributes that suggest modification
            # Some versions of javalang might represent these differently
            elif hasattr(expr, 'expressionl'):
                if isinstance(expr.expressionl, javalang.tree.MemberReference):
                    modified.add(expr.expressionl.member)
            elif hasattr(expr, 'expression') and isinstance(expr.expression, javalang.tree.MemberReference):
                # This might be a unary operation (prefix/postfix)
                modified.add(expr.expression.member)
        elif isinstance(stmt, javalang.tree.BlockStatement):
            for sub_stmt in stmt.statements:
                modified.update(self._extract_modified_variables(sub_stmt))
        
        return modified
    
    def _analyze_loop_termination(self, condition_node, loop_body):
        """
        Analyze if a loop can terminate by checking if condition variables are modified
        in a way that could make the condition false.
        Returns: (is_infinite, reason)
        """
        if condition_node is None:
            return True, "No condition"
        
        # Check for literal true
        if isinstance(condition_node, javalang.tree.Literal):
            if condition_node.value == "true" or condition_node.value == "1":
                return True, "Always true literal"
        
        # Check for binary operations that are always true
        if isinstance(condition_node, javalang.tree.BinaryOperation):
            # Check for expressions like 1==1, true==true, etc.
            if isinstance(condition_node.operandl, javalang.tree.Literal) and \
               isinstance(condition_node.operandr, javalang.tree.Literal):
                left_val = str(condition_node.operandl.value)
                right_val = str(condition_node.operandr.value)
                op = condition_node.operator
                
                if op == "==" and left_val == right_val:
                    return True, "Always true comparison"
                if op == "!=" and left_val != right_val:
                    return True, "Always true comparison"
                # Check numeric comparisons that are always true
                try:
                    left_num = float(left_val) if left_val.replace('.', '').replace('-', '').isdigit() else None
                    right_num = float(right_val) if right_val.replace('.', '').replace('-', '').isdigit() else None
                    if left_num is not None and right_num is not None:
                        if op == "<" and left_num < right_num:
                            return True, "Always true comparison"
                        if op == ">" and left_num > right_num:
                            return True, "Always true comparison"
                        if op == "<=" and left_num <= right_num:
                            return True, "Always true comparison"
                        if op == ">=" and left_num >= right_num:
                            return True, "Always true comparison"
                except:
                    pass
        
        # Extract variables from condition
        condition_vars = self._extract_variables_from_expression(condition_node)
        if not condition_vars:
            # No variables in condition, check if it's always true
            cond_text = ""
            if condition_node.position:
                cond_text = self._get_statement_text(condition_node.position.line).lower()
                cond_clean = re.sub(r'\s+', '', cond_text)
                cond_only = re.sub(r'^(while|for)\s*\(', '', cond_clean)
                cond_only = re.sub(r'\)\s*\{?$', '', cond_only)
                
                infinite_patterns = ["true", "1==1", "true==true", "1!=0", "true!=false", 
                                   "(true)", "(1==1)", "1<2", "2>1", "true||false", "1", 
                                   "true&&true", "!false"]
                if cond_only in infinite_patterns or cond_clean in infinite_patterns:
                    return True, "Always true pattern"
            return False, "No variables to analyze"
        
        # Extract modified variables from loop body and track modification types
        modified_vars = set()
        modification_directions = {}  # Track if variables are incremented/decremented
        
        if loop_body:
            if isinstance(loop_body, javalang.tree.BlockStatement):
                for stmt in loop_body.statements:
                    modified_vars.update(self._extract_modified_variables(stmt))
                    # Analyze modification direction
                    self._analyze_modification_direction(stmt, modification_directions)
            else:
                modified_vars.update(self._extract_modified_variables(loop_body))
                self._analyze_modification_direction(loop_body, modification_directions)
        
        # Check if any condition variable is modified
        condition_vars_modified = condition_vars.intersection(modified_vars)
        
        if not condition_vars_modified:
            # Condition variables are not modified in loop body - likely infinite
            # Unless condition is checking something external
            return True, f"Condition variables {condition_vars} not modified in loop body"
        
        # Analyze the direction of modification relative to condition
        # For example: while (i > 0) with i++ would be infinite, but i-- would terminate
        
        if isinstance(condition_node, javalang.tree.BinaryOperation):
            op = condition_node.operator
            left = condition_node.operandl
            right = condition_node.operandr
            
            # Check if left is a variable and right is a constant
            if isinstance(left, javalang.tree.MemberReference) and isinstance(right, javalang.tree.Literal):
                var_name = left.member
                if var_name in condition_vars_modified:
                    # Analyze modification direction
                    mod_dir = modification_directions.get(var_name, "unknown")
                    right_val = str(right.value)
                    
                    # For > operator: variable > constant
                    # If variable is only incremented, condition stays true (infinite)
                    if op == ">" or op == ">=":
                        if mod_dir == "increment":
                            return True, f"Variable {var_name} is incremented, condition {var_name} {op} {right_val} stays true"
                        elif mod_dir == "decrement":
                            return False, f"Variable {var_name} is decremented, condition {var_name} {op} {right_val} can become false"
                    
                    # For < operator: variable < constant
                    # If variable is only decremented, condition stays true (infinite)
                    if op == "<" or op == "<=":
                        if mod_dir == "decrement":
                            return True, f"Variable {var_name} is decremented, condition {var_name} {op} {right_val} stays true"
                        elif mod_dir == "increment":
                            return False, f"Variable {var_name} is incremented, condition {var_name} {op} {right_val} can become false"
            
            # Check if right is a variable and left is a constant
            if isinstance(right, javalang.tree.MemberReference) and isinstance(left, javalang.tree.Literal):
                var_name = right.member
                if var_name in condition_vars_modified:
                    mod_dir = modification_directions.get(var_name, "unknown")
                    left_val = str(left.value)
                    
                    # For > operator: constant > variable
                    # If variable is only decremented, condition stays true (infinite)
                    if op == ">":
                        if mod_dir == "decrement":
                            return True, f"Variable {var_name} is decremented, condition {left_val} {op} {var_name} stays true"
                        elif mod_dir == "increment":
                            return False, f"Variable {var_name} is incremented, condition {left_val} {op} {var_name} can become false"
                    
                    # For < operator: constant < variable
                    # If variable is only incremented, condition stays true (infinite)
                    if op == "<":
                        if mod_dir == "increment":
                            return True, f"Variable {var_name} is incremented, condition {left_val} {op} {var_name} stays true"
                        elif mod_dir == "decrement":
                            return False, f"Variable {var_name} is decremented, condition {left_val} {op} {var_name} can become false"
        
        # If we can't determine, assume it might terminate (conservative approach)
        return False, "Unable to determine - assuming might terminate"
    
    def _analyze_modification_direction(self, stmt, modification_directions):
        """Analyze if a statement increments or decrements variables"""
        if isinstance(stmt, javalang.tree.StatementExpression):
            expr = stmt.expression
            if isinstance(expr, javalang.tree.Assignment):
                # Check assignment operators (compound assignments like +=, -=)
                if hasattr(expr, 'operator'):
                    op = expr.operator
                    if isinstance(expr.expressionl, javalang.tree.MemberReference):
                        var_name = expr.expressionl.member
                        if op == "+=":
                            modification_directions[var_name] = "increment"
                        elif op == "-=":
                            modification_directions[var_name] = "decrement"
                
                # Check for assignments like a = a + 1 or a = a - 1 (regular assignments)
                # This handles both cases: with operator="=" and without operator attribute
                if isinstance(expr.expressionl, javalang.tree.MemberReference) and \
                   isinstance(expr.value, javalang.tree.BinaryOperation):
                    var_name = expr.expressionl.member
                    bin_op = expr.value
                    # Check if it's a = a + constant or a = a - constant
                    if isinstance(bin_op.operandl, javalang.tree.MemberReference) and \
                       bin_op.operandl.member == var_name and \
                       isinstance(bin_op.operandr, javalang.tree.Literal):
                        if bin_op.operator == "+":
                            # a = a + constant (increment)
                            modification_directions[var_name] = "increment"
                        elif bin_op.operator == "-":
                            # a = a - constant (decrement)
                            modification_directions[var_name] = "decrement"
                    # Check if it's a = constant + a or a = constant - a
                    elif isinstance(bin_op.operandr, javalang.tree.MemberReference) and \
                         bin_op.operandr.member == var_name and \
                         isinstance(bin_op.operandl, javalang.tree.Literal):
                        if bin_op.operator == "+":
                            # a = constant + a (increment, but direction depends on constant)
                            # For simplicity, treat as increment
                            modification_directions[var_name] = "increment"
                        elif bin_op.operator == "-":
                            # a = constant - a (this is unusual, but would be decrement-like)
                            modification_directions[var_name] = "decrement"
            elif isinstance(expr, javalang.tree.MemberReference):
                # Check for postfix/prefix increment/decrement
                var_name = expr.member
                if hasattr(expr, 'postfix_operators') and expr.postfix_operators:
                    if '++' in expr.postfix_operators:
                        modification_directions[var_name] = "increment"
                    elif '--' in expr.postfix_operators:
                        modification_directions[var_name] = "decrement"
                elif hasattr(expr, 'prefix_operators') and expr.prefix_operators:
                    if '++' in expr.prefix_operators:
                        modification_directions[var_name] = "increment"
                    elif '--' in expr.prefix_operators:
                        modification_directions[var_name] = "decrement"
        elif isinstance(stmt, javalang.tree.BlockStatement):
            for sub_stmt in stmt.statements:
                self._analyze_modification_direction(sub_stmt, modification_directions)
    
    def _is_always_false_condition(self, condition_node):
        """Check if a condition is always false (loop never runs)"""
        if condition_node is None:
            return False
        
        # Check for literal false
        if isinstance(condition_node, javalang.tree.Literal):
            if condition_node.value == "false" or condition_node.value == "0":
                return True
        
        # Check for binary operations that are always false
        if isinstance(condition_node, javalang.tree.BinaryOperation):
            if isinstance(condition_node.operandl, javalang.tree.Literal) and \
               isinstance(condition_node.operandr, javalang.tree.Literal):
                left_val = str(condition_node.operandl.value)
                right_val = str(condition_node.operandr.value)
                op = condition_node.operator
                
                if op == "==" and left_val != right_val:
                    return True
                if op == "!=" and left_val == right_val:
                    return True
                if op == "<" and float(left_val) >= float(right_val) if left_val.isdigit() and right_val.isdigit() else False:
                    return True
                if op == ">" and float(left_val) <= float(right_val) if left_val.isdigit() and right_val.isdigit() else False:
                    return True
        
        # Check condition text for common never-run patterns
        if condition_node.position:
            cond_text = self._get_statement_text(condition_node.position.line).lower()
            cond_clean = re.sub(r'\s+', '', cond_text)
            cond_only = re.sub(r'^(while|for)\s*\(', '', cond_clean)
            cond_only = re.sub(r'\)\s*\{?$', '', cond_only)
            
            never_run_patterns = ["false", "0", "1==0", "false==true", "1>2", "2<1", 
                                 "(false)", "(1==0)", "true&&false", "!true"]
            if cond_only in never_run_patterns or cond_clean in never_run_patterns:
                return True
        
        return False
    
    def _is_infinite_loop_condition(self, condition_node):
        """Check if a condition is always true (infinite loop) - simplified version"""
        if condition_node is None:
            return True
        
        # Check for literal true
        if isinstance(condition_node, javalang.tree.Literal):
            if condition_node.value == "true" or condition_node.value == "1":
                return True
        
        # Check for binary operations that are always true
        if isinstance(condition_node, javalang.tree.BinaryOperation):
            if isinstance(condition_node.operandl, javalang.tree.Literal) and \
               isinstance(condition_node.operandr, javalang.tree.Literal):
                left_val = str(condition_node.operandl.value)
                right_val = str(condition_node.operandr.value)
                op = condition_node.operator
                
                if op == "==" and left_val == right_val:
                    return True
                if op == "!=" and left_val != right_val:
                    return True
        
        # Check condition text for common infinite loop patterns
        if condition_node.position:
            cond_text = self._get_statement_text(condition_node.position.line).lower()
            cond_clean = re.sub(r'\s+', '', cond_text)
            cond_only = re.sub(r'^(while|for)\s*\(', '', cond_clean)
            cond_only = re.sub(r'\)\s*\{?$', '', cond_only)
            
            infinite_patterns = ["true", "1==1", "true==true", "1!=0", "true!=false", 
                               "(true)", "(1==1)", "1<2", "2>1", "true||false", "1", 
                               "true&&true", "!false"]
            if cond_only in infinite_patterns or cond_clean in infinite_patterns:
                return True
        
        return False
    
    def _process_method_invocation(self, invocation_node):
        """Process a method invocation - connect caller directly to callee and back (no intermediate nodes)"""
        method_name = invocation_node.member if hasattr(invocation_node, 'member') else "?"
        
        # Save caller's current block and method (where the call happens)
        caller_block = self.current_block
        caller_method = self.call_stack[-1][0] if self.call_stack else None
        
        # Add the method call statement to the current block
        line_no = invocation_node.position.line if invocation_node.position else "?"
        call_text = self._get_statement_text(line_no)
        if "label" not in self.cfg.nodes[caller_block]:
            self.cfg.nodes[caller_block]['label'] = ""
        self.cfg.nodes[caller_block]['label'] += f"\nL{line_no}: {call_text}"
        
        # Check if the method exists and has been processed
        if method_name in self.method_map:
            # Ensure the method has been processed (lazy processing)
            if method_name not in self.method_entries:
                # Save current state
                saved_block = self.current_block
                # Process the method now (this will push it onto the stack and then pop it)
                self._process_method(self.method_map[method_name])
                # Restore caller's block (the method processing changed current_block)
                self.current_block = saved_block
        
        # Check if we have the method entry stored
        if method_name in self.method_entries:
            # Connect caller block directly to method entry (no intermediate call node)
            method_entry = self.method_entries[method_name]
            self._connect_blocks(caller_block, method_entry)
            
            # Push the called method onto the call stack
            # This ensures that when we process blocks in the called method's context,
            # they get the called method's color
            # Note: The called method's blocks are already created, but we need to
            # ensure exit blocks connect back with proper color context
            self.call_stack.append((method_name, method_entry))
            
            # Create a continuation block for after the method returns
            # Temporarily pop the called method to get caller's color for continuation block
            self.call_stack.pop()
            continuation_block = self._new_block("")
            # Ensure continuation block has caller's color
            if caller_method:
                self.node_method_map[continuation_block] = caller_method
            
            # Connect all method exits directly back to continuation block (no intermediate return node)
            # The exit blocks should already have the called method's color
            if method_name in self.method_exits:
                for exit_block in self.method_exits[method_name]:
                    self._connect_blocks(exit_block, continuation_block)
                    # Ensure exit blocks have the called method's color
                    if exit_block not in self.node_method_map:
                        self.node_method_map[exit_block] = method_name
            else:
                # If no exits stored, try to find them by searching from method entry
                exit_blocks = []
                for node in self.cfg.nodes():
                    if "METHOD EXIT" in self.cfg.nodes[node].get("label", "") and \
                       self._is_reachable_from(method_entry, node):
                        exit_blocks.append(node)
                        self._connect_blocks(node, continuation_block)
                        # Ensure exit blocks have the called method's color
                        if node not in self.node_method_map:
                            self.node_method_map[node] = method_name
                # Store found exits for future use
                if exit_blocks:
                    self.method_exits[method_name] = exit_blocks
            
            # Set current block to continuation (execution continues here after method returns)
            # The continuation block already has the caller's color
            self.current_block = continuation_block
        else:
            # Method not found - execution just continues from current block
            # The method call statement is already added to caller_block
            pass
    
    def _is_reachable_from(self, start_node, target_node):
        """Check if target_node is reachable from start_node using DFS"""
        visited = set()
        stack = [start_node]
        
        while stack:
            node = stack.pop()
            if node == target_node:
                return True
            if node in visited:
                continue
            visited.add(node)
            for _, dst in self.cfg.out_edges(node):
                if dst not in visited:
                    stack.append(dst)
        return False

    def visualize(self, format="svg", theme="light"):
        """Generate a visual representation of the CFG and return SVG content"""
        dot = Digraph(format=format)
        dot.attr('node', shape='box', style='rounded,filled', fontname='Courier')
        dot.attr('edge', arrowhead='vee')
        
        # Theme-aware colors
        if theme == "dark":
            default_color = '#2d2d2d'  # Dark background
            default_text_color = '#e0e0e0'  # Light text
            default_edge_color = '#8b8b8b'  # Lighter edges
            dot.attr('graph', bgcolor='#000000')  # Black background to match container
        else:
            default_color = '#e0f7fa'  # Light background
            default_text_color = '#000000'  # Dark text
            default_edge_color = '#000000'  # Dark edges
            dot.attr('graph', bgcolor='#ffffff')  # White background to match container
        
        dot.attr('edge', color=default_edge_color)
        
        for node in self.cfg.nodes():
            label = self.cfg.nodes[node].get("label", node)
            
            # Get color for this node based on method assignment
            color = default_color
            if node in self.node_method_map:
                method_name = self.node_method_map[node]
                if method_name in self.method_colors:
                    color = self.method_colors[method_name]
                    # Adjust color for dark theme
                    if theme == "dark":
                        color = self._darken_color(color)
            
            dot.node(node, label=label, fillcolor=color, fontcolor=default_text_color)
        
        for src, dst in self.cfg.edges():
            dot.edge(src, dst, color=default_edge_color)
        
        # Render to bytes and return SVG content
        svg_bytes = dot.pipe()
        svg_content = svg_bytes.decode('utf-8')
        
        # Post-process SVG to match container background
        if theme == "dark":
            svg_content = self._apply_dark_theme_to_svg(svg_content)
        else:
            svg_content = self._apply_light_theme_to_svg(svg_content)
        
        return svg_content
    
    def _darken_color(self, color):
        """Darken a hex color for dark theme"""
        if color.startswith('#'):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            # Darken by 40%
            r = max(0, int(r * 0.6))
            g = max(0, int(g * 0.6))
            b = max(0, int(b * 0.6))
            return f"#{r:02x}{g:02x}{b:02x}"
        return color
    
    def _apply_dark_theme_to_svg(self, svg_content):
        """Apply dark theme styling to SVG content"""
        import re
        # Set SVG element background color to match container (black)
        # Remove existing style attribute if present, then add new one
        svg_content = re.sub(r'<svg[^>]*style="[^"]*"', '<svg', svg_content, count=1)
        svg_content = re.sub(r'<svg([^>]*)>', r'<svg\1 style="background-color: #000000;">', svg_content, count=1)
        # Also update any Graphviz-generated background rectangles
        svg_content = re.sub(r'fill="#1e1e1e"', 'fill="#000000"', svg_content)
        svg_content = re.sub(r'fill="#00000000"', 'fill="#000000"', svg_content)  # Handle transparent fills that should be black
        return svg_content
    
    def _apply_light_theme_to_svg(self, svg_content):
        """Apply light theme styling to SVG content"""
        import re
        # Set SVG element background color to match container (white)
        # Remove existing style attribute if present, then add new one
        svg_content = re.sub(r'<svg[^>]*style="[^"]*"', '<svg', svg_content, count=1)
        svg_content = re.sub(r'<svg([^>]*)>', r'<svg\1 style="background-color: #ffffff;">', svg_content, count=1)
        # Also update any Graphviz-generated background rectangles
        svg_content = re.sub(r'fill="#ffffff00"', 'fill="#ffffff"', svg_content)  # Handle transparent fills that should be white
        return svg_content
    