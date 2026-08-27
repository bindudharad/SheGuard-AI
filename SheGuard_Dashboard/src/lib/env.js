// Environment variable utilities for Vite
export function getEnv(key, defaultValue = '') {
  const value = import.meta.env[key];
  return value !== undefined && value !== '' ? value : defaultValue;
}

export function getRequiredEnv(key) {
  const value = import.meta.env[key];
  if (value === undefined || value === '') {
    throw new Error('Missing required environment variable: ' + key);
  }
  return value;
}
