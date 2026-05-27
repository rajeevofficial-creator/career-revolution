# Email Setup for Career Revolution

## **Real Email Verification System**

The application now has a complete email verification system that can send **real emails** for:
1. **Account verification** after registration
2. **Welcome emails** after verification
3. **Password reset** (coming soon)

## **Two Modes of Operation:**

### **1. Development Mode (Default)**
- **Simulated emails** - Verification URLs printed to console
- **No SMTP configuration needed**
- **Good for testing** without real email setup

### **2. Production Mode (Real Emails)**
- **Real emails sent via SMTP**
- **Requires SMTP configuration**
- **Supports Gmail, Outlook, SendGrid, etc.**

## **Quick Setup for Gmail:**

### **Step 1: Create App Password (Gmail)**
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** if not already enabled
3. Go to **App passwords**
4. Select **Mail** as app and **Other** as device
5. Name it "Career Revolution"
6. Copy the 16-character app password

### **Step 2: Configure .env file**
Create a `.env` file in the project root:

```env
# Email Configuration for Gmail
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-character-app-password  # ← Use App Password here!
EMAIL_FROM=your-email@gmail.com
EMAIL_FROM_NAME=Career Revolution

# Application URLs
APP_URL=http://localhost:8000
FRONTEND_URL=http://localhost
```

### **Step 3: Test Email Sending**
1. Restart the backend
2. Register a new account
3. Check your email for verification link
4. Click link to verify account
5. Receive welcome email

## **Alternative Email Services:**

### **SendGrid (Recommended for Production)**
```env
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

### **Outlook/Hotmail**
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
```

### **AWS SES**
```env
SMTP_SERVER=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=your-ses-smtp-username
SMTP_PASSWORD=your-ses-smtp-password
```

## **Testing Without Real Email:**

If you don't want to configure real email yet, the system will:
1. **Print verification URLs** to console/logs
2. **Simulate email sending** for testing
3. **Allow manual verification** via admin endpoints

### **Manual Verification (Development Only):**
```bash
# Verify any user's email
POST /admin/verify-email/{user_id}

# Reset password
POST /admin/reset-password/{user_id}?new_password=your-new-password
```

## **Email Templates:**

The system sends beautifully formatted HTML emails with:
- **Branded headers** with Career Revolution logo/colors
- **Clear call-to-action buttons**
- **Mobile-responsive design**
- **Plain text fallback**

## **Security Notes:**

1. **Never commit `.env` file** to version control
2. **Use App Passwords** for Gmail (not your main password)
3. **Environment variables** for sensitive data
4. **Email validation** to prevent spam

## **Troubleshooting:**

### **Common Issues:**

1. **"SMTP credentials not configured"**
   - Check if `.env` file exists
   - Verify SMTP_USERNAME and SMTP_PASSWORD are set

2. **Gmail authentication errors**
   - Enable "Less secure app access" OR use App Password
   - Check if 2-Step Verification is enabled

3. **Emails going to spam**
   - Verify SPF/DKIM records for your domain
   - Use a professional email service (SendGrid, AWS SES)

4. **Connection refused**
   - Check firewall/antivirus blocking SMTP
   - Try port 465 with SSL instead of 587 with STARTTLS

## **Next Steps:**

1. **Configure your `.env` file** with Gmail credentials
2. **Test registration flow** with real emails
3. **Monitor email delivery** in your inbox
4. **Consider professional email service** for production

The system is now ready to send **real verification emails** to users!