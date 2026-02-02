import React, { useState } from 'react';
import './FileSidebar.css';

const FileSidebar = ({ isOpen, onClose, fileStructure, onFileSelect, currentFilePath }) => {

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

  const buildFileTree = (structure, level = 0) => {
    const items = [];
    for (const key in structure) {
      if (key === '_type') continue;
      const item = structure[key];
      if (item._type === 'folder') {
        items.push(
          <li key={key} style={{ paddingLeft: level > 0 ? '20px' : '0' }}>
            <div className="folder">
              <span className="folder-name">📁 {key}</span>
            </div>
            <ul>{buildFileTree(item, level + 1)}</ul>
          </li>
        );
      } else if (item._type === 'file' && key.endsWith('.java')) {
        const fileKey = item.path || key;
        const isSelected = currentFilePath === fileKey;
        items.push(
          <li
            key={key}
            style={{ paddingLeft: level > 0 ? '20px' : '0' }}
            onClick={() => {
              onFileSelect(item.file, fileKey);
            }}
            className={`file-item ${isSelected ? 'file-item-active' : ''}`.trim()}
          >
            <div className="file java">☕ {key}</div>
          </li>
        );
      }
    }
    return items;
  };

  return (
    <>
      <div 
        className={`sidebar-backdrop ${isOpen ? 'show' : ''}`} 
        onClick={onClose}
      ></div>
      <div className={`file-sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-header d-flex justify-content-between align-items-center">
          <h5 className="mb-0">Explorer</h5>
          <button className="btn btn-sm btn-outline-secondary" onClick={onClose}>
            <i className="bi bi-x-lg"></i>
          </button>
        </div>
        <div className="sidebar-content">
          <div className="d-flex justify-content-between align-items-center mb-2 px-2 pt-2">
            <h6 className="mb-0">FILES</h6>
          </div>
          <div className="file-tree">
            {Object.keys(fileStructure).length > 0 ? (
              <ul>{buildFileTree(fileStructure)}</ul>
            ) : (
              <div className="file-explorer-empty">
                <div className="empty-state-icon">📁</div>
                <p className="empty-state-text">No files uploaded</p>
                {/* Reuse the hidden folder upload input from Model page via its id */}
                <label
                  htmlFor="folderUpload"
                  className="btn clarifai-btn empty-state-button"
                >
                  📂 Upload Folder
                </label>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

export default FileSidebar;

