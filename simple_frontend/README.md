# Career Revolution - Simple Frontend

A lightweight HTML/JavaScript frontend for testing the Career Revolution Phase 1 API.

## Features

- ✅ **User Authentication**: Login/Register with JWT tokens
- ✅ **Document Management**: Upload CVs, certifications, portfolios
- ✅ **Profile Management**: Edit user profile information
- ✅ **Dashboard**: View statistics and progress
- ✅ **Responsive Design**: Works on desktop and mobile
- ✅ **Drag & Drop**: Easy file upload with drag & drop support
- ✅ **Real-time Updates**: Automatic data refresh after actions

## File Structure

```
simple_frontend/
├── index.html          # Main HTML page
├── app.js             # All JavaScript functionality
├── style.css          # Additional CSS styles
└── README.md          # This file
```

## Setup Instructions

### 1. Start the Backend API
Make sure the Career Revolution backend is running:

```bash
cd C:\Users\rajeev\.openclaw\workspace\career_revolution
python run.py
```

The API will start at: `http://localhost:8000`

### 2. Open the Frontend
Simply open `index.html` in your browser:
- Double-click the file, or
- Open with: `file:///C:/Users/rajeev/.openclaw/workspace/career_revolution/simple_frontend/index.html`

### 3. Test the Application

#### First-time Setup:
1. **Register a new account** using the email form in the hero section
2. **Login** with your credentials
3. **Upload documents** (CVs, certifications, etc.)
4. **Edit your profile** with career preferences
5. **View your dashboard** with statistics

#### Sample Test Flow:
1. Register: `test@example.com` / `SecurePass123`
2. Login with the same credentials
3. Upload a sample PDF or DOCX file
4. Check the documents list updates
5. Edit profile information
6. Logout and login again to verify persistence

## API Integration

The frontend connects to these backend endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/register` | POST | User registration |
| `/auth/login` | POST | User login (JWT) |
| `/dashboard` | GET | User dashboard data |
| `/documents` | GET | List user documents |
| `/documents/upload` | POST | Upload document |
| `/documents/{id}` | DELETE | Delete document |
| `/profile` | PUT | Update profile |

## Features in Detail

### Authentication System
- JWT token storage in localStorage
- Automatic token refresh on page reload
- Protected routes (requires login for uploads)
- User session persistence

### Document Upload
- Drag & drop file upload
- File type detection (resume, certification, portfolio)
- Progress indicators
- File size validation (10MB limit)
- Multiple file upload support

### User Interface
- **Dashboard**: Profile completion, document count, skill count
- **Document List**: View all uploaded files with status
- **Profile Editor**: Update career preferences and contact info
- **Responsive Design**: Mobile-friendly Bootstrap layout
- **Toast Notifications**: Action feedback system

### Data Management
- Automatic data refresh after uploads/deletes
- Local storage for user session
- Real-time API status monitoring
- Error handling with user-friendly messages

## Browser Compatibility

Tested and works on:
- Chrome 90+
- Firefox 88+
- Edge 90+
- Safari 14+

## Development Notes

### No Build Process Required
This is a pure HTML/JS/CSS frontend with no build step. Just open the HTML file in a browser.

### Dependencies
- **Bootstrap 5.3**: CSS framework for responsive design
- **Font Awesome 6**: Icons
- **Native JavaScript**: No external JS frameworks

### Security Notes
- JWT tokens stored in localStorage (for demo purposes)
- In production, consider more secure storage options
- All API calls include proper authorization headers
- File uploads include type validation

## Troubleshooting

### Common Issues:

1. **"API Offline" message**
   - Make sure the backend is running: `python run.py`
   - Check console for CORS errors

2. **File upload fails**
   - Check file size (max 10MB)
   - Ensure you're logged in
   - Check browser console for errors

3. **Login doesn't persist**
   - Clear browser cache and try again
   - Check localStorage in DevTools (F12)

4. **Styling issues**
   - Ensure internet connection for CDN resources
   - Check browser console for failed resource loads

### Debugging:
1. Open browser DevTools (F12)
2. Check Console tab for errors
3. Check Network tab for API calls
4. Check Application tab for localStorage

## Next Steps

This simple frontend demonstrates Phase 1 functionality. For production:

1. **Build a React/Vue frontend** with proper state management
2. **Add form validation** with better error handling
3. **Implement file preview** for uploaded documents
4. **Add pagination** for document lists
5. **Implement offline support** with service workers
6. **Add testing** with Jest/Cypress

## License

Part of the Career Revolution project - Proprietary