import React, { useState, useRef, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { useTheme } from '../contexts/ThemeContext';
import ASTVisualization from '../components/ASTVisualization';
import CFGVisualization from '../components/CFGVisualization';
import FileSidebar from '../components/FileSidebar';
import './Model.css';

const Model = () => {
  const { theme } = useTheme();
  const [code, setCode] = useState('');
  const [astOutput, setAstOutput] = useState('');
  const [commentsOutput, setCommentsOutput] = useState('');
  const [astData, setAstData] = useState(null);
  const [isGraphicalView, setIsGraphicalView] = useState(false);
  const [isLoading, setIsLoading] = useState({ ast: false, comments: false, cfg: false });
  const [fileStructure, setFileStructure] = useState({});
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [currentFilePath, setCurrentFilePath] = useState(null);
  const [showNamingModal, setShowNamingModal] = useState(false);
  const [submissionName, setSubmissionName] = useState('');
  const [pendingCode, setPendingCode] = useState('');
  const [relationships, setRelationships] = useState({ association: [], aggregation: [], composition: [] });
  const [selectedRelationshipType, setSelectedRelationshipType] = useState(null);
  const editorRef = useRef(null);
  const folderUploadRef = useRef(null);

  const handleEditorDidMount = (editor) => {
    editorRef.current = editor;
  };

  const generateDefaultName = (code) => {
    if (!code || !code.trim()) {
      // Fallback to timestamp-based name if no code
      const now = new Date();
      const timestamp = now.toISOString().slice(0, 10).replace(/-/g, '');
      const time = now.toTimeString().slice(0, 5).replace(':', '');
      return `Submission-${timestamp}-${time}`;
    }
    // Try to extract class name from code
    const classMatch = code.match(/class\s+(\w+)/);
    if (classMatch && classMatch[1]) {
      return classMatch[1];
    }
    // Fallback to timestamp-based name
    const now = new Date();
    const timestamp = now.toISOString().slice(0, 10).replace(/-/g, '');
    const time = now.toTimeString().slice(0, 5).replace(':', '');
    return `Submission-${timestamp}-${time}`;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const codeToSubmit = editorRef.current?.getValue() || code;
    
    if (!codeToSubmit.trim()) {
      alert('Please enter some code');
      return;
    }

    // Store code and show naming modal
    setPendingCode(codeToSubmit);
    // Start with empty name - default will be shown as placeholder
    setSubmissionName('');
    setShowNamingModal(true);
  };

  const handleConfirmSubmit = async () => {
    const codeToSubmit = pendingCode;
    // Use trimmed name if provided, otherwise use default
    const nameToUse = submissionName.trim() || generateDefaultName(codeToSubmit);
    
    setShowNamingModal(false);
    setIsLoading({ ast: true, comments: true, cfg: false });
    setAstOutput('');
    setCommentsOutput('');
    setAstData(null);
    setIsGraphicalView(false);

    try {
      const response = await fetch('/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ code: codeToSubmit, submission_name: nameToUse }),
      });

      const data = await response.json();
      setAstOutput(data.ast || 'No AST generated');
      setCommentsOutput(data.comments || 'No comments generated');
      setRelationships(data.relationships || { association: [], aggregation: [], composition: [] });
      
      // Load AST JSON for graphical view
      if (data.cfg_supported) {
        try {
          const astResponse = await fetch('/ast-json', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ code: codeToSubmit }),
          });
          const astJson = await astResponse.json();
          setAstData(astJson);
          if (astJson.relationships) {
            setRelationships(astJson.relationships);
          }
        } catch (error) {
          console.error('Failed to load AST JSON:', error);
          setAstData(null);
        }
      } else {
        setAstData(null);
      }
    } catch (error) {
      console.error('Error:', error);
      setAstOutput('Error: ' + error.message);
      setCommentsOutput('Error: ' + error.message);
    } finally {
      setIsLoading({ ast: false, comments: false, cfg: false });
    }
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file && file.name.endsWith('.java')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const contents = e.target.result;
        setCode(contents);
        if (editorRef.current) {
          editorRef.current.setValue(contents);
        }
      };
      reader.readAsText(file);
    } else {
      alert('Please upload a Java source file (.java)');
    }
  };

  const handleFolderUpload = (event) => {
    const files = Array.from(event.target.files);
    const structure = {};
    
    if (files.length === 0) {
      return;
    }
    
    files.forEach(file => {
      if (file.name.endsWith('.java')) {
        const path = file.webkitRelativePath || file.name;
        const parts = path.split('/');
        let current = structure;
        
        for (let i = 0; i < parts.length - 1; i++) {
          if (!current[parts[i]]) {
            current[parts[i]] = { _type: 'folder' };
          }
          current = current[parts[i]];
        }
        
        current[parts[parts.length - 1]] = {
          _type: 'file',
          file: file,
          path: path,
        };
      }
    });
    
    setFileStructure(structure);
    setIsSidebarOpen(true);
    setCurrentFilePath(null); // Reset current file path
    
    // Reset the input so the same folder can be selected again
    if (event.target) {
      event.target.value = '';
    }
    
    // Load first Java file
    const firstFile = findFirstJavaFile(structure);
    if (firstFile && firstFile.path) {
      setCurrentFilePath(firstFile.path);
      const reader = new FileReader();
      reader.onload = (e) => {
        const contents = e.target.result;
        setCode(contents);
        if (editorRef.current) {
          editorRef.current.setValue(contents);
        }
      };
      reader.readAsText(firstFile.file);
    }
  };

  const findFirstJavaFile = (structure) => {
    for (const key in structure) {
      if (key === '_type') continue;
      if (structure[key]._type === 'file' && key.endsWith('.java')) {
        return structure[key];
      } else if (structure[key]._type === 'folder') {
        const result = findFirstJavaFile(structure[key]);
        if (result) return result;
      }
    }
    return null;
  };

  const findFirstJavaFilePath = (structure, currentPath = '') => {
    for (const key in structure) {
      if (key === '_type') continue;
      const fullPath = currentPath ? `${currentPath}/${key}` : key;
      if (structure[key]._type === 'file' && key.endsWith('.java')) {
        return fullPath;
      } else if (structure[key]._type === 'folder') {
        const result = findFirstJavaFilePath(structure[key], fullPath);
        if (result) return result;
      }
    }
    return null;
  };

  const loadFileFromStructure = (file, filePath) => {
    setCurrentFilePath(filePath);
    const reader = new FileReader();
    reader.onload = (e) => {
      const contents = e.target.result;
      setCode(contents);
      if (editorRef.current) {
        editorRef.current.setValue(contents);
      }
    };
    reader.readAsText(file);
  };

  const copyToClipboard = async (text, type) => {
    try {
      // Extract plain text from HTML if needed
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = text;
      const plainText = tempDiv.textContent || tempDiv.innerText || text;
      
      // Try modern clipboard API first
      if (navigator.clipboard && navigator.clipboard.writeText) {
        try {
          await navigator.clipboard.writeText(plainText);
          showCopyFeedback(type, true);
          return;
        } catch (clipboardError) {
          console.warn('Clipboard API failed, trying fallback:', clipboardError);
          // Fall through to fallback method
        }
      }
      
      // Fallback method: create a temporary textarea element
      const textarea = document.createElement('textarea');
      textarea.value = plainText;
      textarea.style.position = 'fixed';
      textarea.style.left = '-999999px';
      textarea.style.top = '-999999px';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      
      try {
        const successful = document.execCommand('copy');
        document.body.removeChild(textarea);
        
        if (successful) {
          showCopyFeedback(type, true);
        } else {
          throw new Error('execCommand copy failed');
        }
      } catch (fallbackError) {
        document.body.removeChild(textarea);
        throw fallbackError;
      }
    } catch (err) {
      console.error('Failed to copy:', err);
      showCopyFeedback(type, false);
    }
  };

  const showCopyFeedback = (type, success) => {
    const button = document.querySelector(`[data-copy-type="${type}"]`);
    if (button) {
      const originalText = button.innerHTML;
      if (success) {
        button.innerHTML = '<i class="bi bi-check"></i> Copied!';
        button.style.color = '#28a745';
        setTimeout(() => {
          button.innerHTML = originalText;
          button.style.color = '';
        }, 2000);
      } else {
        button.innerHTML = '<i class="bi bi-x"></i> Failed';
        button.style.color = '#dc3545';
        setTimeout(() => {
          button.innerHTML = originalText;
          button.style.color = '';
        }, 2000);
      }
    }
  };

  return (
    <div className="model-section" style={{ paddingTop: '70px' }}>
      {/* Submission Naming Modal */}
      {showNamingModal && (
        <div className="modal-overlay" onClick={() => setShowNamingModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h5 className="modal-title">Name Your Submission</h5>
              <button
                type="button"
                className="modal-close"
                onClick={() => setShowNamingModal(false)}
                aria-label="Close"
              >
                <i className="bi bi-x-lg"></i>
              </button>
            </div>
            <div className="modal-body">
              <label htmlFor="submission-name-input" className="form-label">
                Submission Name
              </label>
              <input
                type="text"
                id="submission-name-input"
                className="form-control"
                placeholder={pendingCode ? generateDefaultName(pendingCode) : 'Enter submission name...'}
                value={submissionName}
                onChange={(e) => setSubmissionName(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleConfirmSubmit();
                  }
                }}
                autoFocus
              />
              {pendingCode && (
                <p className="modal-help-text">
                  Leave empty to use default name: <strong>{generateDefaultName(pendingCode)}</strong>
                </p>
              )}
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowNamingModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary clarifai-btn"
                onClick={handleConfirmSubmit}
              >
                Submit
              </button>
            </div>
          </div>
        </div>
      )}
      
      <div className="container-fluid" style={{ maxWidth: '1400px', width: '100%' }}>
        {!isSidebarOpen && (
          <button
            className="file-sidebar-toggle"
            onClick={() => setIsSidebarOpen(true)}
            title="Open file explorer"
          >
            <i className="bi bi-chevron-right"></i>
          </button>
        )}
        <FileSidebar
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          fileStructure={fileStructure}
          onFileSelect={loadFileFromStructure}
          currentFilePath={currentFilePath}
        />

        <section className="model-section-content">
          <form onSubmit={handleSubmit} className="code-form">
            <div className="mb-3">
              <div className="d-flex justify-content-between align-items-center mb-2">
                <label className="form-label">Java Code Input</label>
                <div className="d-flex gap-2">
                  <input
                    type="file"
                    id="fileUpload"
                    accept=".java"
                    className="d-none"
                    onChange={handleFileUpload}
                  />
                  <input
                    ref={folderUploadRef}
                    type="file"
                    id="folderUpload"
                    webkitdirectory=""
                    directory=""
                    multiple
                    className="d-none"
                    onChange={handleFolderUpload}
                  />
                  <label htmlFor="fileUpload" className="btn btn-sm clarifai-btn" style={{ margin: 0, marginBottom: '10px', fontSize: '0.9rem', padding: '6px 12px' }}>
                    📁 Upload Java File
                  </label>
                  <label htmlFor="folderUpload" className="btn btn-sm clarifai-btn" style={{ margin: 0, marginBottom: '10px', fontSize: '0.9rem', padding: '6px 12px' }}>
                    📂 Upload Folder
                  </label>
                  <button
                    type="button"
                    className="btn btn-sm clarifai-btn"
                    style={{ margin: 0, marginBottom: '10px', fontSize: '0.9rem', padding: '6px 12px' }}
                    onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                  >
                    <i className="bi bi-folder2-open"></i>
                  </button>
                </div>
              </div>
              <div id="editorContainer" style={{ height: '450px', border: '1px solid var(--border-color)', borderRadius: '12px' }}>
                <Editor
                  height="450px"
                  defaultLanguage="java"
                  value={code}
                  theme={theme === 'dark' ? 'vs-dark' : 'vs'}
                  onChange={(value) => setCode(value || '')}
                  onMount={handleEditorDidMount}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    lineNumbers: 'on',
                    formatOnPaste: true,
                    formatOnType: true,
                  }}
                />
              </div>
            </div>
            <div className="d-flex justify-content-center">
              <button type="submit" className="btn btn-primary clarifai-btn">
                Submit Code
              </button>
            </div>
          </form>
        </section>

        {/* Output Section */}
        <section className="output-section" id="output-section">
          <div className="container-fluid code-form" style={{ marginBottom: '40px', borderRadius: '12px', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }}>
            <div className="output-container">
              {/* Relationships Dropdown */}
              {(relationships.association.length > 0 || relationships.aggregation.length > 0 || relationships.composition.length > 0) && (
                <div className="relationships-section mb-3" style={{
                  padding: '15px',
                  borderRadius: '12px',
                  backgroundColor: theme === 'dark' ? 'var(--bg-secondary)' : '#f8f9fa',
                  border: `1px solid ${theme === 'dark' ? 'var(--border-color)' : '#dee2e6'}`
                }}>
                  <label className="form-label mb-2" style={{ fontWeight: '600' }}>Class Relationships</label>
                  <div className="d-flex gap-2 flex-wrap align-items-center mb-2">
                    <select
                      className="form-select form-select-sm"
                      value={selectedRelationshipType || ''}
                      onChange={(e) => setSelectedRelationshipType(e.target.value || null)}
                      style={{
                        maxWidth: '250px',
                        backgroundColor: theme === 'dark' ? 'var(--bg-primary)' : '#ffffff',
                        color: theme === 'dark' ? 'var(--text-primary)' : '#000',
                        border: `1px solid ${theme === 'dark' ? 'var(--border-color)' : '#ccc'}`
                      }}
                    >
                      <option value="">Select Relationship Type</option>
                      {relationships.association.length > 0 && (
                        <option value="association">Association ({relationships.association.length})</option>
                      )}
                      {relationships.aggregation.length > 0 && (
                        <option value="aggregation">Aggregation ({relationships.aggregation.length})</option>
                      )}
                      {relationships.composition.length > 0 && (
                        <option value="composition">Composition ({relationships.composition.length})</option>
                      )}
                    </select>
                    {selectedRelationshipType && (
                      <button
                        className="btn btn-sm btn-outline-secondary"
                        onClick={() => setSelectedRelationshipType(null)}
                        style={{
                          backgroundColor: theme === 'dark' ? 'var(--bg-secondary)' : '#ffffff',
                          border: `1px solid ${theme === 'dark' ? 'var(--border-color)' : '#ccc'}`,
                          color: theme === 'dark' ? 'var(--text-primary)' : '#000',
                        }}
                      >
                        Clear
                      </button>
                    )}
                  </div>
                  {selectedRelationshipType && relationships[selectedRelationshipType] && relationships[selectedRelationshipType].length > 0 && (
                    <div className="relationships-list" style={{
                      maxHeight: '300px',
                      overflowY: 'auto',
                      padding: '10px',
                      borderRadius: '8px',
                      backgroundColor: theme === 'dark' ? 'var(--bg-primary)' : '#ffffff',
                      border: `1px solid ${theme === 'dark' ? 'var(--border-color)' : '#dee2e6'}`
                    }}>
                      <h6 style={{ 
                        marginBottom: '10px', 
                        color: theme === 'dark' ? 'var(--text-primary)' : '#000',
                        textTransform: 'capitalize'
                      }}>
                        {selectedRelationshipType} Relationships:
                      </h6>
                      <div className="list-group">
                        {relationships[selectedRelationshipType].map((rel, index) => (
                          <div
                            key={index}
                            className="list-group-item"
                            style={{
                              marginBottom: '8px',
                              padding: '12px',
                              borderRadius: '6px',
                              backgroundColor: theme === 'dark' ? 'var(--bg-secondary)' : '#f8f9fa',
                              border: `1px solid ${theme === 'dark' ? 'var(--border-color)' : '#dee2e6'}`,
                              cursor: 'pointer',
                              transition: 'all 0.2s'
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.backgroundColor = theme === 'dark' ? 'var(--bg-primary)' : '#e9ecef';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.backgroundColor = theme === 'dark' ? 'var(--bg-secondary)' : '#f8f9fa';
                            }}
                            onClick={() => {
                              // Scroll to class in AST if possible
                              const classElement = document.querySelector(`[data-class="${rel.from}"]`);
                              if (classElement) {
                                classElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                classElement.style.backgroundColor = theme === 'dark' ? 'rgba(138, 43, 226, 0.3)' : 'rgba(138, 43, 226, 0.1)';
                                setTimeout(() => {
                                  classElement.style.backgroundColor = '';
                                }, 2000);
                              }
                            }}
                          >
                            <div style={{ 
                              fontWeight: '600',
                              color: theme === 'dark' ? 'var(--text-primary)' : '#000',
                              marginBottom: '4px'
                            }}>
                              <span style={{ color: theme === 'dark' ? '#8a2be2' : '#6f42c1' }}>{rel.from}</span>
                              {' → '}
                              <span style={{ color: theme === 'dark' ? '#8a2be2' : '#6f42c1' }}>{rel.to}</span>
                            </div>
                            <div style={{ 
                              fontSize: '0.85rem',
                              color: theme === 'dark' ? 'var(--text-secondary)' : '#6c757d'
                            }}>
                              <strong>Via:</strong> {rel.via}
                            </div>
                            {rel.details && (
                              <div style={{ 
                                fontSize: '0.85rem',
                                color: theme === 'dark' ? 'var(--text-secondary)' : '#6c757d',
                                marginTop: '4px'
                              }}>
                                <strong>Details:</strong> {rel.details}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {/* AST Column */}
              <div className="ast-container-section d-flex flex-column position-relative">
                <div className="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
                  <label className="form-label mb-0">Generated AST</label>
                  <div className="d-flex gap-2 flex-wrap align-items-center">
                    {!isGraphicalView && astOutput && (
                      <button
                        className="btn btn-sm btn-outline-secondary"
                        onClick={() => copyToClipboard(astOutput, 'ast')}
                        data-copy-type="ast"
                        style={{
                          backgroundColor: theme === 'dark' ? 'var(--bg-secondary)' : '#ffffff',
                          border: `1px solid ${theme === 'dark' ? 'var(--border-color)' : '#ccc'}`,
                          color: theme === 'dark' ? 'var(--text-primary)' : '#000',
                        }}
                        title="Copy AST to clipboard"
                      >
                        <i className="bi bi-clipboard"></i> Copy
                      </button>
                    )}
                    <button
                      className="btn btn-sm clarifai-btn"
                      onClick={() => setIsGraphicalView(!isGraphicalView)}
                      disabled={!astOutput && !astData}
                      title={!astOutput && !astData ? 'No AST available' : ''}
                    >
                      {isGraphicalView ? 'Switch to Text View' : 'Switch to Graphical View'}
                    </button>
                  </div>
                </div>
                {isGraphicalView ? (
                  <div 
                    className="position-relative ast-output" 
                    style={{ 
                      border: '1px solid var(--border-color)',
                      borderRadius: '12px',
                      overflow: 'hidden',
                      backgroundColor: theme === 'dark' ? 'var(--ast-bg)' : '#ffffff'
                    }}
                  >
                    {isLoading.ast && (
                      <div className="loading-overlay">
                        <i className="bi bi-hourglass-split loading-spinner-icon"></i>
                        <span className="loading-text">Generating AST...</span>
                      </div>
                    )}
                    <ASTVisualization astData={astData} theme={theme} />
                  </div>
                ) : (
                  <div
                    className="form-control ast-output position-relative"
                    style={{
                      fontFamily: 'monospace',
                      backgroundColor: theme === 'dark' ? 'var(--ast-bg)' : '#ffffff',
                      color: theme === 'dark' ? 'var(--text-primary)' : '#000000',
                    }}
                  >
                    {isLoading.ast && (
                      <div className="loading-overlay">
                        <i className="bi bi-hourglass-split loading-spinner-icon"></i>
                        <span className="loading-text">Generating AST...</span>
                      </div>
                    )}
                    <div dangerouslySetInnerHTML={{ __html: astOutput }} />
                  </div>
                )}
              </div>

              {/* Comments Column */}
              <div className="comments-section d-flex flex-column position-relative">
                <div className="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
                  <label className="form-label mb-0">Generated Comments</label>
                  {commentsOutput && (
                    <button
                      className="btn btn-sm btn-outline-secondary"
                      onClick={() => copyToClipboard(commentsOutput, 'comments')}
                      data-copy-type="comments"
                      style={{
                        backgroundColor: theme === 'dark' ? 'var(--bg-secondary)' : '#ffffff',
                        border: `1px solid ${theme === 'dark' ? 'var(--border-color)' : '#ccc'}`,
                        color: theme === 'dark' ? 'var(--text-primary)' : '#000',
                      }}
                      title="Copy comments to clipboard"
                    >
                      <i className="bi bi-clipboard"></i> Copy
                    </button>
                  )}
                </div>
                <div
                  className="form-control comments-output position-relative"
                  style={{
                    fontFamily: 'monospace',
                    backgroundColor: theme === 'dark' ? '#000000' : '#ffffff',
                    color: theme === 'dark' ? 'var(--text-primary)' : '#000000',
                  }}
                >
                  {isLoading.comments && (
                    <div className="loading-overlay">
                      <i className="bi bi-hourglass-split loading-spinner-icon"></i>
                      <span className="loading-text">Generating comments...</span>
                    </div>
                  )}
                  <div dangerouslySetInnerHTML={{ __html: commentsOutput }} />
                </div>
              </div>

              {/* CFG Section */}
              <CFGVisualization
                code={code}
                editorRef={editorRef}
                theme={theme}
                isLoading={isLoading.cfg}
                setIsLoading={(loading) => setIsLoading(prev => ({ ...prev, cfg: loading }))}
              />
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Model;

