import React from 'react';
import './Skeleton.css';

export function Skeleton({ 
  variant = 'rounded', // text, rectangular, rounded, circular
  width, 
  height, 
  className = '', 
  style = {} 
}) {
  const classNames = `skeleton skeleton--${variant} ${className}`;
  const inlineStyles = {
    width: width || (variant === 'text' ? '100%' : 'auto'),
    height: height || (variant === 'text' ? '1em' : '100%'),
    ...style
  };

  return <div className={classNames} style={inlineStyles} />;
}
