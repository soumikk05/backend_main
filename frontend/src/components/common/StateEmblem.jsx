import React from 'react';

/**
 * State Emblem of India (Ashoka Lion Capital with "सत्यमेव जयते")
 * Authentic official vector structure with exact national lion capital details,
 * 24-spoke Ashoka Chakra, galloping horse, bull, and Devanagari motto.
 */
export const StateEmblem = ({ className = '', size = 56, color = '#E5A93C' }) => {
  const isGold = color === '#E5A93C' || color === 'gold' || color === '#d4af37' || color === '#E5A93C';
  const isWhite = color === '#ffffff' || color === '#FFFFFF' || color === 'white';

  const width = size;
  const height = Math.round(size * 1.594); // Official 145.52 x 231.92 aspect ratio

  if (isGold) {
    return (
      <img
        src="/emblem_gold.svg"
        alt="State Emblem of India"
        width={width}
        height={height}
        className={className}
        style={{
          width: `${width}px`,
          height: `${height}px`,
          display: 'inline-block',
          objectFit: 'contain',
        }}
      />
    );
  }

  if (isWhite) {
    return (
      <img
        src="/emblem_white.svg"
        alt="State Emblem of India"
        width={width}
        height={height}
        className={className}
        style={{
          width: `${width}px`,
          height: `${height}px`,
          display: 'inline-block',
          objectFit: 'contain',
        }}
      />
    );
  }

  // Dynamic color mask support for arbitrary colors
  return (
    <div
      role="img"
      aria-label="State Emblem of India"
      className={className}
      style={{
        width: `${width}px`,
        height: `${height}px`,
        backgroundColor: color,
        WebkitMaskImage: 'url(/emblem.svg)',
        WebkitMaskRepeat: 'no-repeat',
        WebkitMaskPosition: 'center',
        WebkitMaskSize: 'contain',
        maskImage: 'url(/emblem.svg)',
        maskRepeat: 'no-repeat',
        maskPosition: 'center',
        maskSize: 'contain',
        display: 'inline-block',
      }}
    />
  );
};
