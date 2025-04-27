import React from 'react';

export const Input = ({ className = '', ...props }) => {
  return (
    <input
      {...props}
      className={`px-3 py-2 rounded-md border bg-gray-800 border-gray-700 placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring focus:ring-indigo-500 focus:ring-opacity-50 ${className}`}
    />
  );
};