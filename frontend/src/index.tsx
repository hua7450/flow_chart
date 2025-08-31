import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

// Suppress ResizeObserver loop errors more aggressively
const resizeObserverErr = window.console.error;
window.console.error = (...args: any[]) => {
  if (args && args[0] && typeof args[0] === 'string' && 
      (args[0].includes('ResizeObserver loop') || 
       args[0].includes('ResizeObserver loop completed') ||
       args[0].includes('ResizeObserver loop limit'))) {
    return;
  }
  resizeObserverErr(...args);
};

// Also catch unhandled errors
window.addEventListener('unhandledrejection', function(e) {
  if (e.reason && e.reason.message && 
      (e.reason.message.includes('ResizeObserver loop') ||
       e.reason.message.includes('ResizeObserver loop completed'))) {
    e.preventDefault();
  }
});

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
