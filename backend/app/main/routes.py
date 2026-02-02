# app/main/routes.py
from asyncio.log import logger
import hashlib
import uuid
import os
import networkx as nx
from graphviz import Digraph
from werkzeug import Response
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing
from ..cfg_utils import CFGGenerator 
from app.cfg_utils import CFGGenerator
import javalang # For JavaSyntaxError
from flask import Blueprint, app, request, jsonify, redirect, url_for, current_app, flash, send_from_directory
from flask_login import login_required, current_user, logout_user
from . import main_bp # from app/main/__init__.py
from ..models import CodeSubmission, User # from app/models.py
from .. import db # from app/__init__.py
from ..utils import ( # from app/utils.py
    preprocess_code, format_ast, clean_comment, detect_relationships,
    extract_methods, extract_classes, compute_hash, build_ast_json, wrap_code_if_needed
)


@main_bp.route('/generate-cfg', methods=['POST'])
@login_required
def generate_cfg():
    code = request.json.get('code', '')
    theme = request.json.get('theme', 'light')  # Get theme from request
    
    try:
        # Create CFG generator
        generator = CFGGenerator()
        cfg = generator.generate(code)
        
        # Generate SVG content with theme support
        svg_content = generator.visualize(format="svg", theme=theme)
        
        # Return SVG directly
        return Response(
            svg_content,
            mimetype='image/svg+xml',
            headers={'Content-Disposition': 'inline; filename=cfg.svg'}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@main_bp.route('/', methods=['POST'])
def home():
    # GET requests are handled by React Router via catch-all route in __init__.py
    # This route only handles POST requests for code submission

    # Guard POST requests so only authenticated users may submit code
    if not current_user.is_authenticated:
        if request.is_json:
            return jsonify({'error': 'Authentication required'}), 401
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        try:
            code_input = request.json.get('code', '')
            submission_name_provided = request.json.get('submission_name', '') or ''
            submission_name_provided = submission_name_provided.strip() if submission_name_provided else ''
            
            if not code_input.strip() or code_input == '{{ code_input }}': #
                return jsonify({ #
                    'comments': '<div class="comment-error">Error: No Code Submitted</div>',
                    'ast': '<div class="ast-error">Error: No Code Submitted</div>'
                })

            code_hash = compute_hash(code_input)

            existing_submission = CodeSubmission.query.filter_by( #
                user_id=current_user.id, #
                code_hash=code_hash, #
                is_success=True #
            ).first()

            if existing_submission: #
                ast_output = existing_submission.ast_content #
                comments_output = existing_submission.comments_content #
                relationships = detect_relationships(code_input) #
            else:
                # Wrap code in class if needed (handled in utils functions)
                # Try parsing to catch any remaining errors
                try:
                    wrapped_code, was_wrapped = wrap_code_if_needed(code_input)
                    javalang.parse.parse(wrapped_code)
                except javalang.parser.JavaSyntaxError as e: #
                    line_number = getattr(e.at, 'line', 'unknown') #
                    return jsonify({ #
                        'comments': f'<div class="comment-error">Java Syntax Error (Line {line_number}): {e.description}</div>',
                        'ast': format_ast(code_input) # Still show AST if possible
                    })

                class_structure = extract_classes(code_input) #
                method_structure = extract_methods(code_input) #

                if isinstance(class_structure, dict) and 'error' in class_structure: #
                     return jsonify({'comments': class_structure['error'], 'ast': format_ast(code_input)})
                if isinstance(method_structure, dict) and 'error' in method_structure: #
                     return jsonify({'comments': method_structure['error'], 'ast': format_ast(code_input)})


                ast_output = format_ast(code_input) #
                relationships = detect_relationships(code_input) #
                grouped_comments = {} #

                # Batch processing for faster comment generation
                # Get pipeline reference before processing
                hf_pipeline = current_app.hf_pipeline
                
                # Initialize grouped_comments structure
                for class_name in class_structure.keys():
                    grouped_comments[class_name] = {'class_comment': '', 'method_comments': []}
                for class_name in method_structure.keys():
                    if class_name not in grouped_comments:
                        grouped_comments[class_name] = {'class_comment': '', 'method_comments': []}

                # Batch process all classes and methods together for maximum speed
                if hf_pipeline:
                    # Prepare all inputs for batch processing
                    all_inputs = []
                    input_mapping = []  # Track which input corresponds to which class/method
                    
                    # Add classes
                    for class_name, class_code in class_structure.items():
                        processed_class = preprocess_code(class_code)
                        all_inputs.append(processed_class)
                        input_mapping.append(('class', class_name, None))
                    
                    # Add methods
                    for class_name, methods in method_structure.items():
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
                                        grouped_comments[class_name]['class_comment'] = \
                                            f'<div class="comment-class" id="class_{class_name}">📦 Class: {class_name}\n{comment}</div>'
                                    else:  # method
                                        grouped_comments[class_name]['method_comments'].append(
                                            f'<div class="comment-method" id="method_{class_name}_{method_name}">◆ {class_name}.{method_name}:\n{comment}</div>'
                                        )
                        except Exception as e:
                            # Fallback to sequential if batch fails
                            current_app.logger.error(f"Batch processing failed, falling back to sequential: {e}")
                            # Sequential fallback
                            for class_name, class_code in class_structure.items():
                                try:
                                    processed_class = preprocess_code(class_code)
                                    result = hf_pipeline(processed_class)
                                    comment = clean_comment(result[0]['generated_text'])
                                    grouped_comments[class_name]['class_comment'] = \
                                        f'<div class="comment-class" id="class_{class_name}">📦 Class: {class_name}\n{comment}</div>'
                                except Exception as e2:
                                    print(f"Error generating comment for class {class_name}: {e2}")
                            
                            for class_name, methods in method_structure.items():
                                for method in methods:
                                    try:
                                        processed_method = preprocess_code(method['code'])
                                        result = hf_pipeline(processed_method)
                                        comment = clean_comment(result[0]['generated_text'])
                                        grouped_comments[class_name]['method_comments'].append(
                                            f'<div class="comment-method" id="method_{class_name}_{method["name"]}">◆ {class_name}.{method["name"]}:\n{comment}</div>'
                                        )
                                    except Exception as e2:
                                        print(f"Error generating comment for method {class_name}.{method['name']}: {e2}")

                comments_output_list = [] #
                for class_data in grouped_comments.values(): #
                    if class_data['class_comment']: comments_output_list.append(class_data['class_comment']) #
                    comments_output_list.extend(class_data['method_comments']) #
                comments_output = '\n'.join(comments_output_list) if comments_output_list else "No comments generated" #

                # Generate default name if not provided
                if submission_name_provided and submission_name_provided != '':
                    final_submission_name = submission_name_provided
                else:
                    # Try to extract class name from code
                    import re
                    class_match = re.search(r'class\s+(\w+)', code_input)
                    if class_match:
                        final_submission_name = class_match.group(1)
                    else:
                        # Fallback to timestamp-based name
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                        final_submission_name = f"Submission-{timestamp}"
                
                new_submission = CodeSubmission(
                    user_id=current_user.id,
                    code_content=code_input,
                    submission_name=final_submission_name,
                    ast_content=ast_output,
                    comments_content=comments_output,
                    code_hash=code_hash,
                    is_success=True
                )
                db.session.add(new_submission) #
                db.session.commit() #

            return jsonify({ #
                'comments': comments_output,
                'ast': ast_output,
                'cfg_supported': True, # Indicate CFG generation is supported
                'relationships': relationships, # Include relationship data
            })

        except Exception as e:
            current_app.logger.error(f"Server error in home POST: {str(e)}")
            # Attempt to get code_input and submission_name from request
            code_input_for_error = request.json.get('code', '') if request.is_json else "Unavailable"
            error_submission_name = ''
            if request.is_json:
                error_submission_name = request.json.get('submission_name', '') or ''
                error_submission_name = error_submission_name.strip() if error_submission_name else ''
            
            # Generate error name
            if error_submission_name and error_submission_name != '':
                error_name = f"Failed-{error_submission_name}"
            else:
                # Try to extract class name from code
                import re
                if code_input_for_error and code_input_for_error != "Unavailable":
                    class_match = re.search(r'class\s+(\w+)', code_input_for_error)
                    if class_match:
                        error_name = f"Failed-{class_match.group(1)}"
                    else:
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                        error_name = f"Failed-{timestamp}"
                else:
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    error_name = f"Failed-{timestamp}"
            
            error_submission = CodeSubmission(
                user_id=current_user.id,
                code_content=code_input_for_error,
                submission_name=error_name,
                is_success=False
            )
            db.session.add(error_submission) #
            db.session.commit() #

            return jsonify({ #
                'comments': f"Error: {str(e)}",
                'ast': "AST generation failed",
                'cfg_supported': False  # Indicate CFG generation is not supported
            }), 500



# Dashboard route removed - handled by React Router
# Use /api/dashboard for API data

@main_bp.route('/api/dashboard')
@login_required
def api_dashboard():
    submissions = CodeSubmission.query.filter_by(
        user_id=current_user.id,
        is_success=True
    ).order_by(CodeSubmission.timestamp.desc()).all()
    
    # Calculate user stats
    total_submissions = len(submissions)
    
    # Account creation date - use first submission timestamp as estimate
    # (If User model had created_at, we'd use that instead)
    account_creation = None
    if submissions:
        first_submission = CodeSubmission.query.filter_by(
            user_id=current_user.id,
            is_success=True
        ).order_by(CodeSubmission.timestamp.asc()).first()
        if first_submission and first_submission.timestamp:
            account_creation = first_submission.timestamp.isoformat()
    
    # Account level based on submissions (can be refined later)
    if total_submissions < 5:
        account_level = "Beginner"
    elif total_submissions < 15:
        account_level = "Intermediate"
    elif total_submissions < 30:
        account_level = "Advanced"
    else:
        account_level = "Expert"
    
    return jsonify({
        'username': current_user.username,
        'stats': {
            'total_submissions': total_submissions,
            'account_creation': account_creation,
            'account_level': account_level
        },
        'submissions': [{
            'id': s.id,
            'submission_name': s.submission_name,
            'timestamp': s.timestamp.isoformat() if s.timestamp else None
        } for s in submissions]
    })


# Settings route removed - handled by React Router


@main_bp.route('/delete-account', methods=['POST']) #
@login_required #
def delete_account(): #
    try:
        password = request.form.get('password') #
        if not current_user.check_password(password): #
            return jsonify({'success': False, 'error': 'Incorrect password'}), 401

        user_to_delete = User.query.get(current_user.id) #
        db.session.delete(user_to_delete) #
        db.session.commit() #
        logout_user() #
        return jsonify({'success': True, 'redirect': '/'})
    except Exception as e: #
        db.session.rollback() #
        current_app.logger.error(f"Error deleting account: {e}")
        return jsonify({'success': False, 'error': 'Error deleting account'}), 500


@main_bp.route('/get-submission/<int:submission_id>') #
@login_required #
def get_submission(submission_id): #
    submission = CodeSubmission.query.filter_by( #
        id=submission_id, #
        user_id=current_user.id #
    ).first_or_404()
    return jsonify({ #
        'code_content': submission.code_content, #
        'ast_content': submission.ast_content, #
        'comments_content': submission.comments_content #
    })


@main_bp.route('/rename-submission/<int:submission_id>', methods=['POST']) #
@login_required #
def rename_submission(submission_id): #
    submission = CodeSubmission.query.filter_by( #
        id=submission_id, #
        user_id=current_user.id #
    ).first_or_404()
    new_name = request.json.get('new_name', 'Unnamed Submission') #
    submission.submission_name = new_name #
    db.session.commit() #
    return jsonify({'status': 'success'}) #


@main_bp.route('/delete-submission/<int:submission_id>', methods=['DELETE']) #
@login_required #
def delete_submission(submission_id): #
    try:
        submission = CodeSubmission.query.filter_by( #
            id=submission_id, #
            user_id=current_user.id #
        ).first_or_404()
        db.session.delete(submission) #
        db.session.commit() #
        current_app.logger.debug(f"Successfully deleted submission {submission_id} for user {current_user.username}") #
        return jsonify({'status': 'success'}) #
    except Exception as e: #
        db.session.rollback() #
        current_app.logger.error(f"Error deleting submission {submission_id}: {str(e)}") #
        return jsonify({'status': 'error', 'message': str(e)}), 500 #
    

# app/routes.py

@main_bp.route('/ast-json', methods=['POST'])
def ast_json():
    code = request.json.get('code', '')
    ast_data = build_ast_json(code)
    relationships = detect_relationships(code)
    ast_data['relationships'] = relationships
    return jsonify(ast_data)

@main_bp.route('/process-folder', methods=['POST'])
@login_required
def process_folder():
    try:
        # Get the uploaded files
        uploaded_files = request.files.getlist('files[]')
        
        if not uploaded_files:
            return jsonify({"error": "No files uploaded"}), 400
        
        # Process each file
        results = {}
        for file in uploaded_files:
            if file.filename.endswith('.java'):
                code_content = file.read().decode('utf-8')
                filename = file.filename
                
                # Process the code (similar to your home route)
                try:
                    # Your existing processing logic here
                    ast_output = format_ast(code_content)
                    
                    # Extract classes and methods
                    class_structure = extract_classes(code_content)
                    method_structure = extract_methods(code_content)
                    
                    # Get pipeline reference before threading (to avoid context issues)
                    hf_pipeline = current_app.hf_pipeline
                    
                    # Generate comments using parallel processing (reuse helper functions)
                    def generate_class_comment_folder(class_name, class_code):
                        """Generate comment for a single class (folder processing)"""
                        try:
                            processed_class = preprocess_code(class_code)
                            if hf_pipeline:
                                result = hf_pipeline(processed_class)
                                comment = clean_comment(result[0]['generated_text'])
                                return class_name, f'<div class="comment-class" id="class_{class_name}">📦 Class: {class_name}\n{comment}</div>'
                        except Exception as e:
                            print(f"Error generating comment for class {class_name}: {e}")
                            return class_name, None
                        return class_name, None

                    def generate_method_comment_folder(class_name, method):
                        """Generate comment for a single method (folder processing)"""
                        try:
                            processed_method = preprocess_code(method['code'])
                            if hf_pipeline:
                                result = hf_pipeline(processed_method)
                                comment = clean_comment(result[0]['generated_text'])
                                return (class_name, method['name']), f'<div class="comment-method" id="method_{class_name}_{method["name"]}">◆ {class_name}.{method["name"]}:\n{comment}</div>'
                        except Exception as e:
                            print(f"Error generating comment for method {class_name}.{method['name']}: {e}")
                            return (class_name, method['name']), None
                        return (class_name, method['name']), None

                    # Initialize grouped_comments structure
                    grouped_comments = {}
                    for class_name in class_structure.keys():
                        grouped_comments[class_name] = {'class_comment': '', 'method_comments': []}
                    for class_name in method_structure.keys():
                        if class_name not in grouped_comments:
                            grouped_comments[class_name] = {'class_comment': '', 'method_comments': []}

                    # Process classes and methods in parallel
                    max_workers = min(8, len(class_structure) + sum(len(methods) for methods in method_structure.values()))
                    if max_workers > 0 and hf_pipeline:
                        with ThreadPoolExecutor(max_workers=max_workers) as executor:
                            # Submit all class comment generation tasks
                            class_futures = {
                                executor.submit(generate_class_comment_folder, class_name, class_code): class_name
                                for class_name, class_code in class_structure.items()
                            }
                            
                            # Submit all method comment generation tasks
                            method_futures = {
                                executor.submit(generate_method_comment_folder, class_name, method): (class_name, method['name'])
                                for class_name, methods in method_structure.items()
                                for method in methods
                            }
                            
                            # Collect class comments as they complete
                            for future in as_completed(class_futures):
                                class_name, comment_html = future.result()
                                if comment_html:
                                    grouped_comments[class_name]['class_comment'] = comment_html
                            
                            # Collect method comments as they complete
                            for future in as_completed(method_futures):
                                (class_name, method_name), comment_html = future.result()
                                if comment_html:
                                    grouped_comments[class_name]['method_comments'].append(comment_html)
                    
                    comments_output_list = []
                    for class_data in grouped_comments.values():
                        if class_data['class_comment']: 
                            comments_output_list.append(class_data['class_comment'])
                        comments_output_list.extend(class_data['method_comments'])
                    comments_output = '\n'.join(comments_output_list) if comments_output_list else "No comments generated"
                    
                    # Store results for this file
                    results[filename] = {
                        'ast': ast_output,
                        'comments': comments_output,
                        'code': code_content
                    }
                    
                except Exception as e:
                    results[filename] = {
                        'error': str(e)
                    }
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Model route removed - handled by React Router