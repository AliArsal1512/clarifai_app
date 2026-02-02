import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import './Home.css';

const Home = () => {
  const { theme } = useTheme();
  const [displayedText, setDisplayedText] = useState('');
  const fullText = "Welcome to Clarifai !";

  useEffect(() => {
    // Handle navbar scroll effect
    const handleScroll = () => {
      const navbar = document.querySelector('#mainNavbar');
      if (window.scrollY > 100) {
        navbar?.classList.add('navbar-shrink');
      } else {
        navbar?.classList.remove('navbar-shrink');
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    // Typing animation effect
    setDisplayedText('');
    let currentIndex = 0;
    const typingInterval = setInterval(() => {
      if (currentIndex < fullText.length) {
        setDisplayedText(fullText.substring(0, currentIndex + 1));
        currentIndex++;
      } else {
        clearInterval(typingInterval);
      }
    }, 100); // 100ms per character

    return () => clearInterval(typingInterval);
  }, []); // Run once on mount

  // Split displayed text to identify "Clarifai" part for gradient styling
  const renderAnimatedText = () => {
    const beforeClarifai = "Welcome to ";
    const clarifaiText = "Clarifai";
    const afterClarifai = " !";
    
    const currentText = displayedText;
    const isTyping = currentText.length < fullText.length;
    
    if (currentText.length === 0) {
      return <span className="typing-cursor">|</span>;
    }
    
    if (currentText.length <= beforeClarifai.length) {
      // Typing "Welcome to "
      return (
        <>
          {currentText}
          {isTyping && <span className="typing-cursor">|</span>}
        </>
      );
    } else if (currentText.length <= beforeClarifai.length + clarifaiText.length) {
      // Typing "Clarifai"
      const clarifaiTyped = currentText.substring(beforeClarifai.length);
      return (
        <>
          {beforeClarifai}
          <span className="text-clarifai">{clarifaiTyped}</span>
          {isTyping && <span className="typing-cursor">|</span>}
        </>
      );
    } else {
      // Finished typing "Clarifai", now typing " !"
      const afterClarifaiTyped = currentText.substring(beforeClarifai.length + clarifaiText.length);
      return (
        <>
          {beforeClarifai}
          <span className="text-clarifai">{clarifaiText}</span>
          {afterClarifaiTyped}
          {isTyping && <span className="typing-cursor">|</span>}
        </>
      );
    }
  };

  return (
    <div>
      {/* Hero Section */}
      <section className="hero-section p-8" id="hero-section">
        <div className="hero-divider">
          <h2>{renderAnimatedText()}</h2>
        </div>
        <div className="hero-content">
          <div className="welcome-text mt-4">
            <p className="punch-line">Understanding code has never been easier.</p>
            <p>Powered by AI, Clarifai helps you understand your code by generating comments and also through graphical representations of Abstract Syntax Trees and Control Flow Graphs.</p>
          </div>
          <div className="hero-buttons">
            <a href="#how-it-works" className="how-btn">How it works?</a>
            <Link to="/model" className="try-btn">Try it now</Link>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="mb-4">
        <div className="container">
          <div className="row mb-4">
            <div className="col-12 text-center">
              <h3 className="mb-4">How <span className="text-clarifai">Clarifai</span> Works</h3>
              <p className="text-muted">From raw Java code to comments, AST, and CFG</p>
              <div className="how-divider"></div>
            </div>
          </div>
          <div className="row g-4">
            <div className="col-md-4">
              <div className="card h-100 shadow-sm">
                <div className="card-body text-center">
                  <div className="how-icon"><i className="bi bi-chat-dots-fill" aria-hidden="true"></i></div>
                  <h5 className="card-title">Generate Comments</h5>
                  <p className="card-text">Your Java code is analyzed and summarized into human-friendly explanations. Clarifai highlights classes, methods, and key logic to produce concise comments that you can paste back into your source.</p>
                </div>
              </div>
            </div>
            <div className="col-md-4">
              <div className="card h-100 shadow-sm">
                <div className="card-body text-center">
                  <div className="how-icon"><i className="bi bi-diagram-3-fill" aria-hidden="true"></i></div>
                  <h5 className="card-title">Build the AST</h5>
                  <p className="card-text">The <em>Abstract Syntax Tree (AST)</em> represents the structure of your code (packages, classes, methods, statements). We parse the code and render an interactive tree so you can expand nodes and inspect details.</p>
                </div>
              </div>
            </div>
            <div className="col-md-4">
              <div className="card h-100 shadow-sm">
                <div className="card-body text-center">
                  <div className="how-icon"><i className="bi bi-graph-up-arrow" aria-hidden="true"></i></div>
                  <h5 className="card-title">Generate the CFG</h5>
                  <p className="card-text">The <em>Control Flow Graph (CFG)</em> models how execution moves through your program (branches, loops, and merges). Clarifai renders a zoomable SVG so you can pan, zoom, and inspect paths.</p>
                </div>
              </div>
            </div>
          </div>
          <div className="row mt-4">
            <div className="col-12">
              <div className="card pipeline-card border-0 bg-white shadow-sm">
                <div className="card-body">
                  <h6 className="text-uppercase text-muted mb-3"><strong>Pipeline</strong></h6>
                  <ul className="mb-0">
                    <li>Paste or upload Java code in the editor.</li>
                    <li>Click Submit to get AI-generated comments and the AST preview.</li>
                    <li>Use "Generate CFG" to request the CFG SVG and explore it with zoom and pan.</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Home;

