import React, { useState, useEffect, useRef } from 'react';
import Editor from '@monaco-editor/react';
import { useTheme } from '../contexts/ThemeContext';
import './Dashboard.css';

const Dashboard = () => {
  const { theme } = useTheme();
  const [submissions, setSubmissions] = useState([]);
  const [filteredSubmissions, setFilteredSubmissions] = useState([]);
  const [selectedSubmission, setSelectedSubmission] = useState(null);
  const [viewType, setViewType] = useState('code');
  const [isLoading, setIsLoading] = useState(false);
  const [username, setUsername] = useState('');
  const [stats, setStats] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const codePreviewRef = useRef(null);

  useEffect(() => {
    fetchSubmissions();
  }, []);

  const fetchSubmissions = async () => {
    try {
      const response = await fetch('/api/dashboard', {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setSubmissions(data.submissions || []);
        setFilteredSubmissions(data.submissions || []);
        setUsername(data.username || '');
        setStats(data.stats || null);
      }
    } catch (error) {
      console.error('Failed to fetch submissions:', error);
    }
  };

  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredSubmissions(submissions);
    } else {
      const filtered = submissions.filter(sub =>
        sub.submission_name.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setFilteredSubmissions(filtered);
    }
  }, [searchQuery, submissions]);

  const loadSubmission = async (submissionId) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/get-submission/${submissionId}`, {
        credentials: 'include',
      });
      if (response.ok) {
        const data = await response.json();
        setSelectedSubmission({ ...data, id: submissionId });
        setViewType('code');
        // Scroll to code preview after a short delay to allow state update
        setTimeout(() => {
          if (codePreviewRef.current) {
            codePreviewRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }, 100);
      }
    } catch (error) {
      console.error('Failed to load submission:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const deleteSubmission = async (submissionId) => {
    if (!window.confirm('Are you sure you want to delete this submission?')) {
      return;
    }

    try {
      const response = await fetch(`/delete-submission/${submissionId}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      if (response.ok) {
        const updatedSubmissions = submissions.filter(s => s.id !== submissionId);
        setSubmissions(updatedSubmissions);
        const updatedFiltered = filteredSubmissions.filter(s => s.id !== submissionId);
        setFilteredSubmissions(updatedFiltered);
        if (selectedSubmission && selectedSubmission.id === submissionId) {
          setSelectedSubmission(null);
        }
        // Update stats
        if (stats) {
          setStats({
            ...stats,
            total_submissions: updatedSubmissions.length
          });
        }
      }
    } catch (error) {
      console.error('Failed to delete submission:', error);
    }
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

  const renameSubmission = async (submissionId, newName) => {
    try {
      const response = await fetch(`/rename-submission/${submissionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ new_name: newName }),
      });
      if (response.ok) {
        setSubmissions(submissions.map(s => 
          s.id === submissionId ? { ...s, submission_name: newName } : s
        ));
      }
    } catch (error) {
      console.error('Failed to rename submission:', error);
    }
  };

  return (
    <div className="container-fluid dashboard-section" style={{ maxWidth: '1400px', width: '100%' }}>
      <section>
        <div className="welcome-text align-self-start mb-4">
          <h2>Welcome, <span className="text-gradient">{username}</span></h2>
          <div className="align-self-start mb-4">
            <p>View and manage your code submissions.</p>
          </div>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="stats-cards-container mb-4">
            <div className="stats-card">
              <div className="stats-card-icon">
                <i className="bi bi-code-square"></i>
              </div>
              <div className="stats-card-content">
                <div className="stats-card-value">{stats.total_submissions}</div>
                <div className="stats-card-label">Code Submissions</div>
              </div>
            </div>
            <div className="stats-card">
              <div className="stats-card-icon">
                <i className="bi bi-calendar-check"></i>
              </div>
              <div className="stats-card-content">
                <div className="stats-card-value stats-card-date">
                  {stats.account_creation 
                    ? new Date(stats.account_creation).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                    : 'N/A'}
                </div>
                <div className="stats-card-label">Account Created</div>
              </div>
            </div>
            <div className="stats-card">
              <div className="stats-card-icon">
                <i className="bi bi-trophy"></i>
              </div>
              <div className="stats-card-content">
                <div className="stats-card-value stats-card-level">{stats.account_level}</div>
                <div className="stats-card-label">Account Level</div>
              </div>
            </div>
          </div>
        )}

        <div 
          className={`sidebar-backdrop ${isSidebarOpen ? 'show' : ''}`} 
          onClick={() => setIsSidebarOpen(false)}
        ></div>
        {/* Toggle button when sidebar is closed */}
        {!isSidebarOpen && (
          <button
            className="dashboard-sidebar-toggle"
            onClick={() => setIsSidebarOpen(true)}
            title="Open sidebar"
          >
            <i className="bi bi-chevron-right"></i>
          </button>
        )}
        {/* Sidebar for submissions */}
        <div className={`dashboard-sidebar ${isSidebarOpen ? 'open' : ''}`}>
          <div className="sidebar-header d-flex justify-content-between align-items-center">
                <h5 className="mb-0">Code History</h5>
            <button 
              className="btn btn-sm btn-outline-secondary" 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              title={isSidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            >
              <i className={`bi bi-chevron-${isSidebarOpen ? 'left' : 'right'}`}></i>
            </button>
              </div>
          <div className="sidebar-content">
            {/* Search Bar */}
            {submissions.length > 0 && (
              <div className="sidebar-search-container px-3 pt-2 pb-2">
                <div className="sidebar-search-wrapper">
                  <i className="bi bi-search sidebar-search-icon"></i>
                  <input
                    type="text"
                    className="sidebar-search-input"
                    placeholder="Search submissions..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  {searchQuery && (
                    <button
                      className="sidebar-search-clear"
                      onClick={() => setSearchQuery('')}
                      title="Clear search"
                    >
                      <i className="bi bi-x-lg"></i>
                    </button>
                  )}
                </div>
              </div>
            )}
            
            {submissions.length === 0 ? (
              <p className="text-muted px-3 py-4">No submissions yet</p>
            ) : filteredSubmissions.length === 0 ? (
              <p className="text-muted px-3 py-4">No submissions found</p>
            ) : (
              <div className="submission-list">
                {filteredSubmissions.map(sub => (
                  <SubmissionItem
                    key={sub.id}
                    submission={sub}
                    isSelected={selectedSubmission?.id === sub.id}
                    onSelect={() => loadSubmission(sub.id)}
                    onDelete={() => deleteSubmission(sub.id)}
                    onRename={(newName) => renameSubmission(sub.id, newName)}
                  />
                ))}
              </div>
            )}
          </div>
          </div>

        {/* Main content area */}
        <div className="dashboard-main">
            <div ref={codePreviewRef} className="card h-100">
              <div className="card-header-blue bg-primary text-white">
                <h5 className="mb-0 d-inline">Code Preview</h5>
                <div className="btn-group float-end" role="group">
                  <button
                    type="button"
                    className={`btn btn-sm btn-outline-light ${viewType === 'code' ? 'active' : ''}`}
                    onClick={() => setViewType('code')}
                  >
                    Code
                  </button>
                  <button
                    type="button"
                    className={`btn btn-sm btn-outline-light ${viewType === 'ast' ? 'active' : ''}`}
                    onClick={() => setViewType('ast')}
                  >
                    AST
                  </button>
                  <button
                    type="button"
                    className={`btn btn-sm btn-outline-light ${viewType === 'comments' ? 'active' : ''}`}
                    onClick={() => setViewType('comments')}
                  >
                    Comments
                  </button>
                </div>
              </div>
              <div className="card-body p-0 position-relative" style={{ minHeight: '500px', height: 'auto' }}>
                {isLoading && (
                  <div className="loading-overlay">
                    <div className="spinner-border text-primary"></div>
                    <span className="loading-text">Loading...</span>
                  </div>
                )}
                {selectedSubmission ? (
                  <>
                    {viewType === 'code' && (
                      <div style={{ height: '500px', width: '100%' }}>
                        <Editor
                          height="500px"
                          language="java"
                          value={selectedSubmission.code_content}
                          theme={theme === 'dark' ? 'vs-dark' : 'vs'}
                          options={{
                            readOnly: true,
                            minimap: { enabled: false },
                            fontSize: 14,
                            scrollBeyondLastLine: false,
                            automaticLayout: true,
                          }}
                        />
                      </div>
                    )}
                    {viewType === 'ast' && (
                      <div
                        style={{
                          height: '500px',
                          overflow: 'auto',
                          padding: '15px',
                          backgroundColor: theme === 'dark' ? 'var(--ast-bg)' : '#ffffff',
                          color: theme === 'dark' ? 'var(--text-primary)' : '#000000',
                        }}
                        dangerouslySetInnerHTML={{ __html: selectedSubmission.ast_content }}
                      />
                    )}
                    {viewType === 'comments' && (
                      <div className="position-relative" style={{ height: '500px' }}>
                        {selectedSubmission.comments_content && (
                          <div className="d-flex justify-content-end mb-2 px-3 pt-2">
                            <button
                              className="btn btn-sm btn-outline-secondary"
                              onClick={() => copyToClipboard(selectedSubmission.comments_content, 'comments')}
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
                          </div>
                        )}
                        <div
                          style={{
                            height: 'calc(500px - 50px)',
                            overflow: 'auto',
                            padding: '15px',
                            backgroundColor: theme === 'dark' ? '#000000' : '#ffffff',
                            color: theme === 'dark' ? 'var(--text-primary)' : '#000000',
                          }}
                          dangerouslySetInnerHTML={{ __html: selectedSubmission.comments_content }}
                        />
                      </div>
                    )}
                  </>
                ) : (
                  <div className="code-preview-empty">
                    <div className="empty-state-icon">💻</div>
                    <p className="empty-state-text">Select a submission to preview</p>
                    <p className="empty-state-subtext">Choose a file from the sidebar to view its code, AST, or comments</p>
                  </div>
                )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

const SubmissionItem = ({ submission, isSelected, onSelect, onDelete, onRename }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(submission.submission_name);

  const handleSave = () => {
    if (name !== submission.submission_name) {
      onRename(name);
    }
    setIsEditing(false);
  };

  return (
    <div 
      className={`submission-item ${isSelected ? 'submission-item-active' : ''}`.trim()} 
      onClick={onSelect}
    >
      <div className="submission-item-content">
        {isEditing ? (
          <input
            type="text"
            className="form-control submission-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={handleSave}
            onKeyPress={(e) => e.key === 'Enter' && handleSave()}
            onClick={(e) => e.stopPropagation()}
            autoFocus
          />
        ) : (
          <div className="submission-name-display">
            {submission.submission_name}
          </div>
        )}
        <div className="submission-actions" onClick={(e) => e.stopPropagation()}>
          <button
            className="btn btn-sm btn-outline-secondary"
            onClick={() => setIsEditing(!isEditing)}
            title="Rename"
          >
            <i className="bi bi-pencil"></i>
          </button>
          <button
            className="btn btn-sm btn-outline-danger"
            onClick={onDelete}
            title="Delete"
          >
            <i className="bi bi-trash"></i>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

