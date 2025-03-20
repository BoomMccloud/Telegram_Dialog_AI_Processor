# Lessons


# Scratchpad

APP_ENV=development JWT_SECRET_KEY=your-secure-key PYTHONPATH=. uvicorn app.main:app --reload --port 8000

database name is telegram_dialog_dev

telegramID: 6761933542
+6596456152

tree -L 4 -I 'sessions|tests|scripts|__*|token_logs|response_storage|message_storage|node_modules|frontend'

MessagesPage/
├── index.tsx                    # Main page component
├── components/
│   ├── MessageList/            # List of messages with responses
│   │   ├── MessageCard/        # Individual message + context display
│   │   │   ├── MessageContext  # Historical messages display
│   │   │   ├── MessageContent  # Current message content
│   │   │   └── SuggestedResponse # AI response with actions
│   │   └── MessageFilters      # Search and status filters
│   ├── ResponseEditor/         # Response editing interface
│   │   ├── EditorToolbar      # Edit/Approve/Reject actions
│   │   └── ResponseForm       # Edit form with preview
│   └── ProcessingStatus/       # Status for background operations
└── hooks/
    ├── useMessages            # Message data and operations
    ├── useMessageContext     # Historical message fetching
    └── useProcessing         # Background processing state


┌─────────────────────────────────────────────────────┐
│ MessagesPage                                        │
│  ┌─────────────────────┐    ┌───────────────┐       │
│  │     MessageList    │     │ResponseEditor │       │
│  │  ┌──────────────┐  │     │               │      │
│  │  │ MessageCard  │  │     │               │      │
│  │  │ ┌──────────┐ │  │     │               │      │
│  │  │ │ Context  │ │  │     │               │      │
│  │  │ └──────────┘ │  │     │               │      │
│  │  │ ┌──────────┐ │  │     │               │      │
│  │  │ │Response  │ │  │     │               │      │
│  │  │ └──────────┘ │  │     │               │      │
│  │  └──────────────┘  │     │               │      │
│  └─────────────────────┘     └───────────────┘     │
│  ┌─────────────────────┐                           │
│  │  ProcessingStatus   │                           │
│  └─────────────────────┘                           │
└────────────────────────────────────────────────────┘