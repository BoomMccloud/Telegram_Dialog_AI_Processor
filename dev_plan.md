# Telegram Messages Page Development Plan

## Overview
This document outlines the development plan for the new Telegram messages page, which will be implemented under `/frontend-ui/src/pages/telegram`. The page will handle Telegram authentication, display messages with historical context, and manage AI-generated responses. This plan focuses on maximizing the reuse of existing components while minimizing new code.

## Project Structure

### Path Aliases
The project has proper path alias configuration in both `tsconfig.app.json` and `vite.config.ts`. Use these aliases for imports:
- `@/*` -> `./src/*`
- `@components/*` -> `./src/components/*`
- `@services/*` -> `./src/services/*`
- `@hooks/*` -> `./src/hooks/*`
- `@types/*` -> `./src/types/*`

## Components

### Telegram Messages Page (`/telegram`)
Current implementation status:

1. **Basic Structure**
   - Layout with 12-column grid
   - Three main sections: Message Thread (4 cols), Message Context (5 cols), Response Actions (3 cols)
   - Components properly imported using path aliases

2. **State Management**
   ```typescript
   const [selectedDialogId, setSelectedDialogId] = useState<string | null>(null);
   const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
   const [isLoading, setIsLoading] = useState<boolean>(false);
   const [error, setError] = useState<Error | null>(null);
   ```

3. **Event Handlers**
   - `handleDialogSelect`: Updates selected dialog and resets message selection
   - `handleMessageSelect`: Updates selected message

4. **TODO**
   - Implement data fetching for dialogs
   - Add loading state management using `setIsLoading`
   - Add error handling using `setError`
   - Connect components to real data sources
   - Add initial state loading
   - Implement dialog selection logic

5. **Component Dependencies**
   All required components exist in correct locations:
   - `MainLayout.tsx` in components/Layout
   - `MessageThread.tsx` in components/Messages
   - `ResponseActions.tsx` in components/Messages
   - `MessageContextView` in components/Messages/MessageContextView

## Next Steps
1. Implement dialog fetching and filtering
2. Add loading states and progress indicators
3. Implement error handling and user feedback
4. Connect to message processing pipeline
5. Add response management functionality

## Existing Components to Reuse

### Core Components
```typescript
// From components/Messages/
import { MessageThread } from 'components/Messages/MessageThread';
import { MessageItem } from 'components/Messages/MessageItem';
import { ResponseActions } from 'components/Messages/ResponseActions';

// From components/Auth/
import { ProtectedRoute } from 'components/Auth/ProtectedRoute';
import { QRLogin } from 'components/Auth/QRLogin';
import { SessionManager } from 'components/Auth/SessionManager';

// From components/Layout/
import { MainLayout } from 'components/Layout/MainLayout';
```

## Development Phases

### Phase 1: Core Setup (Week 1)
1. **Page Setup**
   - Create telegram page using `MainLayout`
   - Integrate existing `ProtectedRoute` for auth protection
   - Set up routing in main App component
   - Reuse existing auth flow (`QRLogin`, `SessionManager`)

2. **Message Context Integration**
   - Create `MessageContextView` component
   - Implement `useMessageContext` hook
   - Add historical context endpoint to existing API
   - Integrate with existing message services

### Phase 2: Component Integration (Week 2)
1. **Message Display**
   - Integrate existing `MessageThread` component
   - Add context display to `MessageItem`
   - Connect existing response management
   - Implement context loading states

2. **Response Management**
   - Integrate existing `ResponseActions`
   - Connect to existing API endpoints
   - Reuse existing response processing
   - Add context-aware response generation

### Phase 3: Polish & Testing (Week 3)
1. **Testing & Optimization**
   - Test new components
   - Integration testing with existing components
   - Performance optimization
   - Add context caching

2. **Final Integration**
   - Error handling
   - Loading states
   - Documentation
   - Performance monitoring

## Component Specifications

### New Components

#### MessageContextView
```typescript
interface MessageContextViewProps {
  dialogId: string;
  messageId: string;
  onContextLoad: (context: MessageContext) => void;
  className?: string;
}

interface MessageContext {
  messages: HistoricalMessage[];
  hasMore: boolean;
  isLoading: boolean;
}
```

#### useMessageContext Hook
```typescript
interface UseMessageContextResult {
  context: MessageContext;
  loadMore: () => Promise<void>;
  hasMore: boolean;
  isLoading: boolean;
  error: Error | null;
}

const useMessageContext = (
  dialogId: string,
  messageId: string
): UseMessageContextResult;
```

## API Integration

### Existing Endpoints to Reuse
```
Authentication:
- POST /api/auth/telegram/login
- POST /api/auth/telegram/verify
- POST /api/auth/refresh

Messages:
- GET /api/messages/{dialogId}
- POST /api/responses/generate
- PUT /api/responses/{responseId}
- POST /api/responses/{responseId}/approve
- POST /api/responses/{responseId}/reject
```

### New Endpoint Required
```
Messages:
- GET /api/messages/{messageId}/historical-context
  Parameters:
    - limit: number
    - before: number
    - after: number
  Response:
    {
      messages: HistoricalMessage[];
      hasMore: boolean;
    }
```

## Testing Strategy

1. **New Component Tests**
   - MessageContextView rendering and interaction
   - useMessageContext hook behavior
   - API integration for historical context

2. **Integration Tests**
   - Interaction with existing components
   - Authentication flow
   - Response management
   - Context loading and pagination

3. **Performance Tests**
   - Context loading speed
   - Memory usage with large context
   - Caching effectiveness

## Performance Considerations

1. **Context Loading**
   - Implement pagination for historical messages
   - Cache context data in memory
   - Preload adjacent message contexts
   - Implement virtual scrolling for large contexts

2. **Integration Optimization**
   - Reuse existing data fetching logic
   - Share cached data between components
   - Minimize redundant API calls
   - Use existing state management

## Error Handling

1. **Context Loading Errors**
   - Network failures
   - Invalid message IDs
   - Missing permissions
   - Rate limiting

2. **Integration Errors**
   - Component communication
   - State synchronization
   - API response handling
   - Authentication failures

## Deployment Checklist

1. **Pre-deployment**
   - Test integration with existing components
   - Verify API endpoint compatibility
   - Check performance metrics
   - Review error handling

2. **Deployment**
   - Update API documentation
   - Deploy new endpoint
   - Update frontend routes
   - Monitor error rates

3. **Post-deployment**
   - Monitor context loading performance
   - Track API usage
   - Collect user feedback
   - Optimize based on metrics

## Future Considerations

1. **Potential Enhancements**
   - Advanced context filtering
   - Smarter context preloading
   - Enhanced caching strategies
   - Performance optimizations

2. **Maintenance**
   - Regular dependency updates
   - Performance monitoring
   - Error tracking
   - User feedback collection 