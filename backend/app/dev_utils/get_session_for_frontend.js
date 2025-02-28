// JavaScript snippet to set the mock session ID in localStorage
// Open your browser's developer console and paste this code
// to set the session ID for frontend testing

// Replace with your current mock session ID
const SESSION_ID = "98ce6db8-173c-416c-8910-c9c475125fdd";

// Set the session ID in localStorage
localStorage.setItem('sessionId', SESSION_ID);
console.log(`✅ Session ID set: ${SESSION_ID}`);
console.log(`You can now navigate to the messages page to test the UI`);

// Check the current environment
console.log(`Current API URL: ${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'}`);

// Some debugging tips
console.log("\nDebugging Tips:");
console.log("1. If you see CORS errors, make sure your backend is running with APP_ENV=development");
console.log("2. Check Network tab for API calls to '/api/dialogs/{session_id}'");
console.log("3. If you get 'Invalid or expired session' errors, generate a new session");
console.log("4. To generate a new session run: PYTHONPATH=. python -m app.dev_utils.inject_mock_session"); 