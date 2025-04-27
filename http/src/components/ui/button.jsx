import React from 'react';

export const Button = ({ children, className = '', ...props }) => {
  return (
    <button
      className={`px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white font-medium transition ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};