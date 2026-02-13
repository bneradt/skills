# Azure App Registration Setup

Step-by-step guide to creating the Azure app registration needed for msgraph-kit.

## Prerequisites

- A Microsoft account (personal, work, or school)
- Access to the Azure Portal (free tier works)

## Steps

### 1. Go to Azure Portal

Open [https://portal.azure.com](https://portal.azure.com) and sign in.

### 2. Navigate to App Registrations

- Search for **"App registrations"** in the top search bar, or
- Go to **Microsoft Entra ID** (formerly Azure Active Directory) → **App registrations**

### 3. Create a New Registration

Click **"New registration"** and fill in:

- **Name**: `Kit MS Graph` (or any name you prefer)
- **Supported account types**: Choose based on your needs:
  - **Personal Microsoft accounts only** — if you only use a personal Microsoft/Outlook account
  - **Accounts in any organizational directory and personal Microsoft accounts** — if you use both work/school and personal accounts
- **Redirect URI**: Leave blank (not needed for device code flow)

Click **Register**.

### 4. Enable Public Client Flow

After registration:

1. Go to **Authentication** in the left sidebar
2. Scroll down to **Advanced settings**
3. Set **"Allow public client flows"** to **Yes**
4. Click **Save**

This is required for the device code flow (no client secret needed).

### 5. Add API Permissions

1. Go to **API permissions** in the left sidebar
2. Click **"Add a permission"**
3. Select **Microsoft Graph**
4. Select **Delegated permissions**
5. Search for and add these permissions:
   - `User.Read` (should already be there by default)
   - `Notes.Read`
   - `Notes.ReadWrite`
   - `Notes.Create`
6. Click **"Add permissions"**

You should NOT need admin consent for these permissions — they are all delegated user permissions.

### 6. Copy Your IDs

From the app's **Overview** page, copy:

- **Application (client) ID** → this goes in `.env` as `MSGRAPH_CLIENT_ID`
- **Directory (tenant) ID** → this goes in `.env` as `MSGRAPH_TENANT_ID`

If you selected "Personal Microsoft accounts only", use `consumers` as the tenant ID.
If you selected the multi-tenant option, use `common` as the tenant ID.

### 7. Configure .env

In the msgraph repo:

```bash
cp .env.example .env
```

Edit `.env`:

```
MSGRAPH_CLIENT_ID=your-application-client-id-here
MSGRAPH_TENANT_ID=common
```

### 8. Test Authentication

```bash
python3 scripts/auth_login.py
```

This will print a URL and code. Open the URL in your browser, enter the code, and sign in. On success, you'll see JSON output with your username.

## Troubleshooting

### "AADSTS7000218: The request body must contain the following parameter: 'client_assertion' or 'client_secret'"

The app registration doesn't have public client flows enabled. Go to Authentication → Advanced settings → "Allow public client flows" = Yes.

### "AADSTS65001: The user or administrator has not consented to use the application"

The API permissions haven't been granted. Go to API permissions and ensure all required permissions are added. For personal accounts, no admin consent is needed.

### "AADSTS700016: Application with identifier '...' was not found"

The client ID in `.env` doesn't match the Azure app registration. Double-check the Application (client) ID on the Overview page.

### "AADSTS90002: Tenant '...' not found"

The tenant ID is incorrect. Try using `common` or `consumers` depending on your account type.

## Security Notes

- **No client secret** is stored or needed — device code flow is a public client flow
- **Tokens** are cached in the macOS Keychain (encrypted by the OS)
- **Auth record** (`~/.msgraph-kit/auth_record.json`) contains only non-sensitive account identifiers (tenant ID, username) — no tokens
- The `.env` file contains only the app registration's client ID (public information) and tenant ID
