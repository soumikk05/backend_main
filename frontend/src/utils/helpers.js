/**
 * Returns the CSS variable name for a risk label.
 */
export function riskColor(label) {
  switch (label?.toUpperCase()) {
    case 'LOW':    return 'var(--risk-low)';
    case 'MEDIUM': return 'var(--risk-medium)';
    case 'HIGH':   return 'var(--risk-high)';
    default:       return 'var(--text-muted)';
  }
}

/**
 * Returns the background color for a risk label.
 */
export function riskBgColor(label) {
  switch (label?.toUpperCase()) {
    case 'LOW':    return 'var(--risk-low-bg)';
    case 'MEDIUM': return 'var(--risk-medium-bg)';
    case 'HIGH':   return 'var(--risk-high-bg)';
    default:       return 'transparent';
  }
}

/**
 * Formats a date string for display.
 */
export function formatDate(raw) {
  if (!raw) return '—';
  try {
    const d = new Date(raw);
    if (isNaN(d.getTime())) return raw;
    return d.toLocaleDateString('en-IN', {
      year: 'numeric', month: 'short', day: 'numeric',
    });
  } catch {
    return raw;
  }
}

/**
 * Truncates long strings.
 */
export function truncate(str, max = 50) {
  if (!str) return '';
  return str.length > max ? str.slice(0, max) + '…' : str;
}

/**
 * Creates a file-size-friendly label.
 */
export function formatFileSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

export const formatBytes = formatFileSize;

/**
 * Generates a unique ID for scan history entries.
 */
export function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}

/**
 * Returns an interpolated colour between green, amber, and red based on score (0-100).
 */
export function scoreToHex(score) {
  if (score <= 30)  return '#10B981';
  if (score <= 65)  return '#F59E0B';
  return '#F43F5E';
}
