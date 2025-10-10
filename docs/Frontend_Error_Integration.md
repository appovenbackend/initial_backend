# Frontend Integration Guide - Error Handling

This guide shows how to integrate with the new frontend-optimized JSON error responses in your mobile/web applications.

## Error Response Structure

### Single Field Error
```json
{
  "success": false,
  "error": {
    "type": "validation_error",
    "code": "INVALID_EMAIL",
    "message": "Email format is invalid",
    "userMessage": "Please enter a valid email address like user@domain.com",
    "field": "email",
    "severity": "error"
  },
  "meta": {
    "requestId": "req_123456",
    "timestamp": "2025-10-10T15:23:53+05:30",
    "path": "/api/auth/register",
    "method": "POST"
  }
}
```

### Multiple Field Errors
```json
{
  "success": false,
  "error": {
    "type": "validation_error",
    "code": "FORM_VALIDATION_FAILED",
    "message": "Please correct the errors below",
    "userMessage": "Please fix the highlighted fields and try again",
    "fieldErrors": {
      "email": {
        "message": "Please enter a valid email address",
        "code": "INVALID_EMAIL_FORMAT",
        "severity": "error"
      },
      "password": {
        "message": "Password must be at least 8 characters",
        "code": "PASSWORD_TOO_SHORT",
        "severity": "warning"
      }
    },
    "severity": "error"
  },
  "meta": {
    "requestId": "req_123456",
    "timestamp": "2025-10-10T15:23:53+05:30"
  }
}
```

### Authentication Error
```json
{
  "success": false,
  "error": {
    "type": "authentication_error",
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "userMessage": "The email or password you entered is incorrect. Please try again.",
    "severity": "error"
  },
  "meta": {
    "requestId": "req_123456",
    "timestamp": "2025-10-10T15:23:53+05:30"
  }
}
```

## React Integration Examples

### Basic Error Handler Hook
```jsx
// useApiError.js
import { useState } from 'react';

export const useApiError = () => {
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleApiCall = async (apiCall) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiCall();
      const data = await response.json();

      if (data.success) {
        setIsLoading(false);
        return { success: true, data: data.data };
      } else {
        setError(data.error);
        setIsLoading(false);
        return { success: false, error: data.error };
      }
    } catch (err) {
      setError({
        type: 'network_error',
        message: 'Network error occurred',
        userMessage: 'Please check your internet connection and try again.'
      });
      setIsLoading(false);
      return { success: false, error: error };
    }
  };

  const clearError = () => setError(null);

  return { error, isLoading, handleApiCall, clearError };
};
```

### Form Validation Component
```jsx
// FormField.jsx
import React from 'react';

const FormField = ({ field, error, value, onChange, placeholder }) => {
  const fieldError = error?.fieldErrors?.[field];
  const hasError = fieldError || (error?.field === field);

  return (
    <div className="form-field">
      <input
        type={field === 'password' ? 'password' : 'text'}
        value={value}
        onChange={(e) => onChange(field, e.target.value)}
        placeholder={placeholder}
        className={hasError ? 'error' : ''}
      />
      {hasError && (
        <div className={`error-message ${fieldError?.severity || error?.severity}`}>
          {fieldError?.message || error?.userMessage}
        </div>
      )}
    </div>
  );
};

export default FormField;
```

### Login Form with Error Handling
```jsx
// LoginForm.jsx
import React, { useState } from 'react';
import { useApiError } from './useApiError';
import FormField from './FormField';

const LoginForm = () => {
  const [credentials, setCredentials] = useState({ phone: '', password: '' });
  const { error, isLoading, handleApiCall, clearError } = useApiError();

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearError();

    const result = await handleApiCall(() =>
      fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials)
      })
    );

    if (result.success) {
      // Handle successful login
      console.log('Login successful:', result.data);
    }
  };

  const handleInputChange = (field, value) => {
    setCredentials(prev => ({ ...prev, [field]: value }));
    // Clear field-specific errors when user starts typing
    if (error?.field === field || error?.fieldErrors?.[field]) {
      clearError();
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <FormField
        field="phone"
        error={error}
        value={credentials.phone}
        onChange={handleInputChange}
        placeholder="Phone number"
      />

      <FormField
        field="password"
        error={error}
        value={credentials.password}
        onChange={handleInputChange}
        placeholder="Password"
      />

      {error && error.type === 'authentication_error' && (
        <div className="error-message error">
          {error.userMessage}
        </div>
      )}

      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Logging in...' : 'Login'}
      </button>
    </form>
  );
};

export default LoginForm;
```

## Vue.js Integration Examples

### Vue Composition API Error Handler
```javascript
// composables/useApiError.js
import { ref, computed } from 'vue';

export function useApiError() {
  const error = ref(null);
  const isLoading = ref(false);

  const handleApiCall = async (apiCall) => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await apiCall();
      const data = await response.json();

      if (data.success) {
        isLoading.value = false;
        return { success: true, data: data.data };
      } else {
        error.value = data.error;
        isLoading.value = false;
        return { success: false, error: data.error };
      }
    } catch (err) {
      error.value = {
        type: 'network_error',
        message: 'Network error occurred',
        userMessage: 'Please check your internet connection and try again.'
      };
      isLoading.value = false;
      return { success: false, error: error.value };
    }
  };

  const clearError = () => {
    error.value = null;
  };

  const getFieldError = (field) => {
    if (!error.value) return null;
    return error.value.fieldErrors?.[field] || (error.value.field === field ? error.value : null);
  };

  const hasError = (field) => {
    return getFieldError(field) !== null;
  };

  return {
    error: computed(() => error.value),
    isLoading: computed(() => isLoading.value),
    handleApiCall,
    clearError,
    getFieldError,
    hasError
  };
}
```

### Vue Component with Error Handling
```vue
<template>
  <form @submit.prevent="handleSubmit">
    <div class="form-field">
      <input
        v-model="credentials.phone"
        placeholder="Phone number"
        :class="{ error: hasError('phone') }"
        @input="clearFieldError('phone')"
      />
      <div v-if="getFieldError('phone')" class="error-message">
        {{ getFieldError('phone').userMessage || getFieldError('phone').message }}
      </div>
    </div>

    <div class="form-field">
      <input
        v-model="credentials.password"
        type="password"
        placeholder="Password"
        :class="{ error: hasError('password') }"
        @input="clearFieldError('password')"
      />
      <div v-if="getFieldError('password')" class="error-message">
        {{ getFieldError('password').userMessage || getFieldError('password').message }}
      </div>
    </div>

    <div v-if="error && error.type === 'authentication_error'" class="error-message">
      {{ error.userMessage }}
    </div>

    <button type="submit" :disabled="isLoading">
      {{ isLoading ? 'Logging in...' : 'Login' }}
    </button>
  </form>
</template>

<script setup>
import { ref } from 'vue';
import { useApiError } from '@/composables/useApiError';

const credentials = ref({ phone: '', password: '' });
const { error, isLoading, handleApiCall, clearError, getFieldError, hasError } = useApiError();

const handleSubmit = async () => {
  const result = await handleApiCall(() =>
    fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials.value)
    })
  );

  if (result.success) {
    console.log('Login successful:', result.data);
  }
};

const clearFieldError = (field) => {
  // Clear field-specific errors when user starts typing
  if (error.value?.field === field || error.value?.fieldErrors?.[field]) {
    clearError();
  }
};
</script>
```

## TypeScript Integration

### Error Response Types
```typescript
// types/api-errors.ts
export interface ApiError {
  type: 'validation_error' | 'authentication_error' | 'authorization_error' |
        'database_error' | 'payment_error' | 'rate_limit_error' | 'system_error';
  code: string;
  message: string;
  userMessage: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  field?: string;
  fieldErrors?: Record<string, {
    message: string;
    code: string;
    severity: string;
  }>;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: ApiError;
  meta?: {
    requestId: string;
    timestamp: string;
    path?: string;
    method?: string;
  };
}

export interface FieldError {
  message: string;
  code: string;
  severity: string;
}
```

### API Client with Error Handling
```typescript
// services/api-client.ts
import type { ApiResponse, ApiError } from '@/types/api-errors';

export class ApiClient {
  private baseURL: string;

  constructor(baseURL: string = '/api') {
    this.baseURL = baseURL;
  }

  async request<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      const data: ApiResponse<T> = await response.json();

      if (!data.success && data.error) {
        throw new ApiError(data.error);
      }

      return data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }

      // Network or parsing error
      throw new ApiError({
        type: 'network_error',
        code: 'NETWORK_ERROR',
        message: 'Network request failed',
        userMessage: 'Please check your internet connection and try again.',
        severity: 'high'
      });
    }
  }

  async post<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async get<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' });
  }
}

// Custom Error Class
export class ApiError extends Error {
  public readonly type: string;
  public readonly code: string;
  public readonly userMessage: string;
  public readonly severity: string;
  public readonly field?: string;
  public readonly fieldErrors?: Record<string, FieldError>;

  constructor(error: ApiError) {
    super(error.message);
    this.name = 'ApiError';
    this.type = error.type;
    this.code = error.code;
    this.userMessage = error.userMessage;
    this.severity = error.severity;
    this.field = error.field;
    this.fieldErrors = error.fieldErrors;
  }

  // Helper methods for error handling
  isValidationError(): boolean {
    return this.type === 'validation_error';
  }

  isAuthenticationError(): boolean {
    return this.type === 'authentication_error';
  }

  isFieldError(fieldName: string): boolean {
    return this.field === fieldName || !!this.fieldErrors?.[fieldName];
  }

  getFieldError(fieldName: string): FieldError | undefined {
    return this.fieldErrors?.[fieldName];
  }
}
```

### Usage Example
```typescript
// services/auth-service.ts
import { ApiClient, ApiError } from './api-client';

export class AuthService {
  private client: ApiClient;

  constructor() {
    this.client = new ApiClient();
  }

  async login(phone: string, password: string) {
    try {
      const response = await this.client.post('/auth/login', {
        phone,
        password
      });

      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        // Handle specific error types
        if (error.isValidationError()) {
          // Handle validation errors
          if (error.fieldErrors) {
            // Multiple field errors
            Object.keys(error.fieldErrors).forEach(field => {
              console.log(`Field ${field}: ${error.fieldErrors[field].message}`);
            });
          }
        } else if (error.isAuthenticationError()) {
          // Handle authentication errors
          console.log('Authentication failed:', error.userMessage);
        }
      }
      throw error;
    }
  }

  async register(userData: RegisterData) {
    try {
      const response = await this.client.post('/auth/register', userData);
      return response.data;
    } catch (error) {
      if (error instanceof ApiError && error.isValidationError()) {
        // Extract field errors for form display
        const fieldErrors: Record<string, string> = {};
        if (error.fieldErrors) {
          Object.keys(error.fieldErrors).forEach(field => {
            fieldErrors[field] = error.fieldErrors[field].message;
          });
        }
        return { fieldErrors };
      }
      throw error;
    }
  }
}
```

## Error Handling Best Practices

### 1. User-Friendly Messages
Always use `error.userMessage` for display to users, not `error.message` which is for debugging.

### 2. Field-Specific Error Handling
```javascript
// React example
const getFieldError = (fieldName) => {
  if (error?.field === fieldName) {
    return error.userMessage;
  }
  return error?.fieldErrors?.[fieldName]?.message;
};
```

### 3. Error Type-Based Actions
```javascript
// Handle different error types appropriately
switch(error.type) {
  case 'validation_error':
    // Highlight form fields, show field-specific messages
    break;
  case 'authentication_error':
    // Clear stored tokens, redirect to login
    break;
  case 'authorization_error':
    // Show access denied message
    break;
  case 'rate_limit_error':
    // Show retry message with timer
    break;
  case 'network_error':
    // Suggest checking connection
    break;
}
```

### 4. Error Severity Styling
```css
.error-message {
  color: red;
  font-size: 14px;
  margin-top: 4px;
}

.error-message.warning {
  color: orange;
}

.error-message.error {
  color: red;
}

.error-message.critical {
  color: darkred;
  font-weight: bold;
}
```

## Common Error Codes Reference

| Error Type | Code | Description | Frontend Action |
|------------|------|-------------|-----------------|
| validation_error | INVALID_EMAIL | Email format invalid | Show field error |
| validation_error | PASSWORD_TOO_SHORT | Password < 8 chars | Show field error |
| authentication_error | INVALID_CREDENTIALS | Wrong login details | Show general error |
| authorization_error | ACCESS_DENIED | Insufficient permissions | Show access denied |
| rate_limit_error | TOO_MANY_REQUESTS | Rate limit exceeded | Show retry message |
| business_logic_error | EVENT_NOT_FOUND | Event doesn't exist | Show not found message |
| payment_error | PAYMENT_FAILED | Payment processing failed | Show payment error |

## Testing Error Scenarios

### Mock Error Responses for Testing
```javascript
// test-utils.js
export const mockErrorResponses = {
  validationError: {
    success: false,
    error: {
      type: "validation_error",
      code: "INVALID_EMAIL",
      message: "Email format is invalid",
      userMessage: "Please enter a valid email address",
      field: "email",
      severity: "error"
    }
  },

  multiFieldError: {
    success: false,
    error: {
      type: "validation_error",
      code: "FORM_VALIDATION_FAILED",
      message: "Multiple validation errors",
      userMessage: "Please fix the errors below",
      fieldErrors: {
        email: {
          message: "Invalid email format",
          code: "INVALID_EMAIL",
          severity: "error"
        },
        password: {
          message: "Password too short",
          code: "PASSWORD_TOO_SHORT",
          severity: "warning"
        }
      }
    }
  },

  authError: {
    success: false,
    error: {
      type: "authentication_error",
      code: "INVALID_CREDENTIALS",
      message: "Authentication failed",
      userMessage: "Invalid credentials provided",
      severity: "error"
    }
  }
};
```

This comprehensive error handling system makes it much easier for your frontend applications to provide a better user experience with clear, actionable error messages and appropriate error handling for different scenarios.
